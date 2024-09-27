import requests
from dataclasses import dataclass
from typing import Optional, TypeVar, Callable, Dict

from requests.auth import HTTPBasicAuth

@dataclass(frozen=True)
class JenkinsQueueExecutable:
  number: int
  url: str

@dataclass(frozen=True)
class JenkinsQueueItem:
  url: str
  buildable: bool
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

@dataclass
class RestClient:
  username: str
  password: str
  base_url: str

  # foo
  def getJenkinsJob(self, job_name: str) -> Optional[JenkinsJob]:
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
          reason=json["queueItem"]["why"]
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
        queue_item = None if not json["executable"] else JenkinsQueueExecutable(
          number = json["executable"]["number"],
          url = json["executable"]["url"]
        )
      )
    )

  A = TypeVar("A")
  def __apiCall(self, path: str, transform: Callable[[Dict],A]) -> Optional[A]:
    url = f"{self.base_url}{path}/api/json"
    response = requests.get(url, auth=HTTPBasicAuth(self.username, self.password))
    if response.status_code == 200:
      return transform( response.json() )
    else:
      print(f"Failed to make REST call to {url}. Status code: {response.status_code}")
      return None
