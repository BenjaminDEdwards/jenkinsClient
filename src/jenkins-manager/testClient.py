import argparse
from Jenkins.Client import RestClient

def main( user_name: str, password: str, base_url: str, job_name: str):
  client = RestClient(
    username=user_name,
    password=password,
    base_url=base_url
  )

  state = client.runJob(job_name)

  if( state.success ):
    print(f"job completed: {state.value}")
    exit(0)
  else:
    print(f"job failed: {state.value}")
    exit(1)

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='Run a Jenkins job via CLI.')

  parser.add_argument('--username', required=True, help='Jenkins username')
  parser.add_argument('--password', required=True, help='Jenkins password')
  parser.add_argument('--base-url', required=True, help='Base URL of the Jenkins instance')
  parser.add_argument('job_name', help='The name of the Jenkins job to run')

  args = parser.parse_args()

  main(args.username, args.password, args['base_url'], args['job_name'])
