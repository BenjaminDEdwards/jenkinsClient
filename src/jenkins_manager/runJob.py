#!/usr/bin/env python3

import argparse
import os
from jenkins_manager.Jenkins.Client import RestClient

def main():
  parser = argparse.ArgumentParser(description='Run a Jenkins job via CLI.')

  parser.add_argument('--username', required=True, help='Jenkins username')
  parser.add_argument('--password', required=True, help='Jenkins password')
  parser.add_argument('--base-url', required=True, help='Base URL of the Jenkins instance')
  parser.add_argument('job_name', help='The name of the Jenkins job to run')

  args = parser.parse_args()

  job_name = args.job_name
  build_run_timeout_seconds = os.getenv('JENKINS_BUILD_TIMEOUT_SECONDS')
  http_timeout = os.getenv('JENKINS_HTTP_TIMEOUT_SECONDS')
  refresh_interval = os.getenv('JENKINS_REFRESH_INTERVAL_SECONDS')
  queue_retries = os.getenv('JENKINS_QUEUE_RETRIES')


  # Initialize the RestClient parameters dictionary
  client_params = {
      'username': args.username,
      'password': args.password,
      'base_url': args.base_url
  }

  if build_run_timeout_seconds is not None:
      client_params['build_run_timeout_seconds'] = int(build_run_timeout_seconds)
  if http_timeout is not None:
      client_params['http_timeout_seconds'] = int(http_timeout)
  if refresh_interval is not None:
      client_params['refresh_interval_seconds'] = int(http_timeout)
  if queue_retries is not None:
      client_params['queue_build_max_retries'] = int(queue_retries)

  # Initialize the RestClient with the parameters
  client = RestClient(**client_params)

  state = client.runJob(job_name)

  if( state.success ):
    print(f"job completed: {state.value}")
    exit(0)
  else:
    print(f"job failed: {state.value}")
    exit(1)

if __name__ == "__main__":
  main()
