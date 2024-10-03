import re
import requests
from dataclasses import dataclass
from typing import Optional, TypeVar, Callable, Dict
from enum import Enum
import time
import signal

from requests.auth import HTTPBasicAuth

@dataclass(frozen=True)
class JenkinsQueueExecutable:
  number: int
  url: str

@dataclass(frozen=True)
class JenkinsQueueItem:
  url: str
  buildable: Optional[bool]
  cancelled: bool
  id: int
  reason: Optional[str]
  executable: Optional[JenkinsQueueExecutable] = None

@dataclass(frozen=True)
class JenkinsJob:
  url: str
  buildable: bool
  next_build_number: int
  in_queue: bool
  queue_item: Optional[JenkinsQueueItem]

class BuildResult(Enum):
  SUCCESS = "SUCCESS"
  FAILURE = "FAILURE"
  ABORTED = "ABORTED"

@dataclass(frozen=True)
class State:
  value: str
  success: bool = False


class JobState(Enum):
  QUEUED = State( "QUEUED" )
  BUILDING = State( "BUILDING")
  COMPLETED = State( "COMPLETED", True )
  FAILED = State( "FAILED", False )
  CANCELLED = State( "CANCELLED", False )
  TIMED_OUT = State( "TIMED_OUT", False )
  UNKNOWN = State( "UNKNOWN", False )


class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException()

@dataclass(frozen=True)
class JenkinsBuild:
  url: str
  number: int
  in_progress: bool
  building: bool
  display_name: Optional[str]
  full_display_name: Optional[str]
  result: Optional[BuildResult]

@dataclass
class RestClient:
  username: str
  password: str
  base_url: str
  log_info: Callable[[str], None] = lambda log_line: print(f"{log_line}")
  max_retries: int = 5
  timeout: int = 5
  refresh_interval_seconds: int = 30
  build_run_timeout_seconds: int = 300 # 5 minutes
  http_timeout_seconds: int = 10

  def buildWithParameters(self, job_name: str) -> Optional[str]:
    url = f"{self.base_url}/job/{job_name}/buildWithParameters"
    response = requests.post(url, auth=HTTPBasicAuth(self.username, self.password))
    if ( response.status_code == 404 ):
      return None
    queue_url = response.headers.get('location', None)
    if not queue_url:
      return None
    
    queue_id = self.__queueItemFromUrl(queue_url)
    if not queue_id:
      return None

    return self.getQueueItem(queue_id)


  def __queueItemFromUrl(self, input: str ) -> Optional[int]:
    pattern = r"/queue/item/(\d+)"
    match = re.search(pattern,input)
    if match:
      return match.group(1)
    return None

  def getJobBuild(self, job_name: str, build_number: int):
    return self.__apiCall(
      f"/job/{job_name}/{build_number}",
      lambda json: JenkinsBuild(
        url = json["url"],
        number = json["number"],
        in_progress = json["inProgress"],
        building = json["building"],
        display_name = json["displayName"],
        result = None if not json.get("result") else BuildResult(json.get("result")),
        full_display_name = json.get("fullDisplayName")
      )
    )

  # foo
  def getJob(self, job_name: str) -> Optional[JenkinsJob]:
    return self.__apiCall(
      f"/job/{job_name}",
      lambda json: JenkinsJob(
        url=json["url"],
        buildable=json["buildable"],
        next_build_number=json["nextBuildNumber"],
        in_queue=json["inQueue"],
        queue_item=None if not json["inQueue"] else JenkinsQueueItem(
          url=json["queueItem"]["url"],
          buildable=json["queueItem"]["buildable"],
          id=json["queueItem"]["id"],
          reason=json["queueItem"]["why"],
          cancelled=json["queueItem"]["cancelled"]
        )
      )
    )

  def getQueueItem(self, queue_id: int) -> Optional[JenkinsQueueItem]:
    return self.__apiCall(
      f"/queue/item/{queue_id}",
      lambda json: JenkinsQueueItem(
        url = json["url"],
        buildable = json["buildable"],
        id = json["id"],
        executable = None if not json.get("executable") else JenkinsQueueExecutable(
          number = json["executable"]["number"],
          url = json["executable"]["url"]
        ),
        reason = json.get("why"),
        cancelled = json.get("cancelled")
      )
    )


  A = TypeVar("A")
  def __apiCall(self, path: str, transform: Callable[[Dict],A]) -> Optional[A]:
    url = f"{self.base_url}{path}/api/json"
    try:
      response = requests.get(url, auth=HTTPBasicAuth(self.username, self.password), timeout=self.http_timeout_seconds)
      if response.status_code == 404:
        return None
      if response.status_code == 200:
        return transform( response.json() )

      self.log_info(f"Failed to make REST call to {url}. Status code: {response.status_code}")
    except requests.Timeout:
      # Handle the case where the request times out
      self.log_info(f"Request to {url} timed out after {self.http_timeout_seconds} seconds")
      return None

    return None


  def queueBuild( self, job_name:str ) -> Optional[JenkinsQueueItem]:
    jenkinsBuild = self.getJob(job_name)
    queueItem: Optional[JenkinsQueueItem] = jenkinsBuild.queue_item
    if (queueItem):
      self.log_info("Using existing queue item")
      return queueItem

    remaining_tries = self.max_retries
    while (queueItem == None and remaining_tries > 0):
      self.log_info(f"kicking off build for {job_name}")
      remaining_tries -= 1
      queueItem = self.buildWithParameters(job_name)
      if (queueItem):
        break
      jenkinsBuild = self.getJob(job_name)
      queueItem = jenkinsBuild.queue_item
      if (queueItem):
        break
      self.log_info("Could not kick off a new build, will retry ( {remaining_tries} attempts remaining )")
      time.sleep(self.timeout)

    return queueItem

  def _runJobInternal(self, job_name: str) -> State:
    new = self.queueBuild(job_name)
    queue_id = new.id
    job_number = 0

    if not queue_id:
      return JobState.FAILED.value
    
    job_state = JobState.QUEUED
    self.log_info(f"Jenkins job queued at: {new.url} - {new.reason}")
    self.log_info(f"Polling for updates every {self.refresh_interval_seconds} seconds...")
    while( job_state == JobState.QUEUED or job_state == JobState.BUILDING ):
      time.sleep(self.refresh_interval_seconds)
      if ( job_state == JobState.QUEUED ):
        item = self.getQueueItem(queue_id)
        self.log_info(f"Build is queued {item.reason}")
        if ( item.cancelled ):
          self.log_info("Queued build has been cancelled")
          job_state = JobState.CANCELLED
          break
        if ( item.executable ):
          self.log_info(f"Build is in progress: {item.executable.url}")
          job_number = item.executable.number
          job_state = JobState.BUILDING
        continue
      if ( job_state == JobState.BUILDING ):
        build = self.getJobBuild(job_name, job_number)
        if ( build.result ):
          if ( build.result == BuildResult.SUCCESS ):
            self.log_info(f"Build {build.display_name} has completed")
            job_state = JobState.COMPLETED
          elif ( build.result == BuildResult.FAILURE ):
            self.log_info(f"Build {build.display_name} has failed")
            job_state = JobState.FAILED
          elif ( build.result == BuildResult.ABORTED ):
            self.log_info(f"Build {build.display_name} has been aborted")
            job_state = JobState.CANCELLED
          else:
            self.log_info(f"Build {build.display_name} has an unknown state: {build.result}")
            job_state = JobState.UNKNOWN
          break
        self.log_info(f"Build {build.display_name} is in progress")
        continue
    
    return job_state.value

  def runJob(self, job_name: str) -> State:
    # Set up the timeout
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(self.build_run_timeout_seconds )  # Set the timeout for 5 minutees (600 seconds)

    try:
      # Call the private method with the original logic
      return self._runJobInternal(job_name)
    
    except TimeoutException:
      self.log_info("Job execution timed out after {self.build_run_timeout_seconds} seconds")
      return JobState.TIMED_OUT.value
    finally:
      # Cancel the alarm if the job finishes before timeout
      signal.alarm(0)


