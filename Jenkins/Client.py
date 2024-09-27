import requests
from dataclasses import dataclass
from typing import Optional

from requests.auth import HTTPBasicAuth

@dataclass(frozen=True)
class JenkinsJob:
  url: str
  buildable: bool
  next_build_number: int

@dataclass
class RestClient:
  username: str
  password: str
  base_url: str

  def getJenkinsJob(self, job_name: str) -> Optional[JenkinsJob]
    url = f"{self.base_url}/job/{job_name}/api/json"
    response = requests.get(url, auth=HTTPBasicAuth(self.username, self.password))
    if response.status_code == 200:
      return JenkinsJob(
        url=response.json()["url"],
        buildable=response.json()["buildable"],
        next_build_number=response.json()["nextBuildNumber"]
      )
    else:
      print(f"Failed to get Jenkins job {job_name}. Status code: {response.status_code}")
      return None
