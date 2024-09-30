from Jenkins.Client import RestClient

def main():
  client = RestClient(
    username="user1",
    password="passme",
    base_url="https://jenkins.test.com"
  )

  job_name = "test"
  print("Running jankins job code")
  jenkins_job = client.getJenkinsJob(job_name)

  if jenkins_job:
    print (f"got jenkins job")
  else:
    print("fail")

if __name__ == "__main__":
  main()