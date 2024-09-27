import requests
from dataclasses import dataclass
from typing import Optional, TypeVar, Callable, Dict

from requests.auth import HTTPBasicAuth

@dataclass(frozen=True)
class JenkinsJob:
  url: str
  buildable: bool
  next_build_number: int

@dataclass(frozen=True)
class JenkinsQueueItem:
  url: str
  buildable: bool
  next_build_number: int

@dataclass
class RestClient:
  username: str
  password: str
  base_url: str

  def getJenkinsJob(self, job_name: str) -> Optional[JenkinsJob]:
    return self.__apiCall(
      f"/job/{job_name}",
      lambda json: JenkinsJob(
        url=json["url"],
        buildable=json["buildable"],
        next_build_number=json["nextBuildNumber"],
        in_queue=json["inQueue"]
      )
    )


  def getQueueItem(self, queue_id: int) -> Optional[JenkinsQueueItem]:
    return self.__apiCall(
      f"/queue/item/{queue_id}",
      lambda json: JenkinsQueueItem(
        url = json["url"],
        buildable = json["buildable"],
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
