# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import boto3
import botocore
import requests
import argparse
import time
from ruamel.yaml import YAML
import subprocess
import os

def get_secret(path):
    with open(path, 'r') as f:
        cred = f.readline().strip('\'')
    f.close()
    return cred

''' global initialization '''
yaml = YAML(typ='safe')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--model_def_file_path', type=str, help='Object storage bucket file path for the training model definition')
    parser.add_argument('--manifest_file_path', type=str, help='Object storage bucket file path for the FfDL manifest', default="")
    parser.add_argument('--training_job_name', type=str, help='Name of the training job', default="training job")
    parser.add_argument('--training_job_description', type=str, help='description of the training job', default="Training ML/DL model")
    parser.add_argument('--training_job_version', type=str, help='version of the training job', default="1.0")
    parser.add_argument('--training_job_gpus', type=float, help='number of gpus for the training job', default=0)
    parser.add_argument('--training_job_cpus', type=float, help='number of cpus for the training job', default=1.0)
    parser.add_argument('--training_job_learners', type=int, help='number of learners for the training job', default=1)
    parser.add_argument('--training_job_memory', type=str, help='Amount of memory for the training job', default="1Gb")
    parser.add_argument('--training_job_framework_name', type=str, help='ML/DL Framework name for the training job', default="tensorflow")
    parser.add_argument('--training_job_framework_version', type=str, help='ML/DL Framework version for the training job', default="latest")
    parser.add_argument('--training_job_command', type=str, help='Exuecution command for the training job', default="echo command not defined")
    parser.add_argument('--training_job_metric_type', type=str, help='Metric storing type for the training job', default="tensorboard")
    parser.add_argument('--training_job_metric_path', type=str, help='Metric storing path for the training job', default="$JOB_STATE_DIR/logs/tb")
    args = parser.parse_args()

    s3_url = get_secret("/app/secrets/s3_url")
    data_bucket_name = get_secret("/app/secrets/training_bucket")
    result_bucket_name = get_secret("/app/secrets/result_bucket")
    s3_access_key_id = get_secret("/app/secrets/s3_access_key_id")
    s3_secret_access_key = get_secret("/app/secrets/s3_secret_access_key")
    ffdl_rest = get_secret("/app/secrets/ffdl_rest")

    model_def_file_path = args.model_def_file_path
    manifest_file_path = args.manifest_file_path
    training_job_name = args.training_job_name
    training_job_description = args.training_job_description
    training_job_version = args.training_job_version
    training_job_gpus = args.training_job_gpus
    training_job_cpus = args.training_job_cpus
    training_job_learners = args.training_job_learners
    training_job_memory = args.training_job_memory
    training_job_framework_name = args.training_job_framework_name
    training_job_framework_version = args.training_job_framework_version
    training_job_command = args.training_job_command
    training_job_metric_type = args.training_job_metric_type
    training_job_metric_path = args.training_job_metric_path

    ffdl_template = {
        "name": training_job_name,
        "description": training_job_description,
        "version": training_job_version,
        "gpus": training_job_gpus,
        "cpus": training_job_cpus,
        "learners": training_job_learners,
        "memory": training_job_memory,
        "data_stores": [
            {
                "id": "cos",
                "type": "mount_cos",
                "training_data": {"container": data_bucket_name},
                "training_results": {"container": result_bucket_name},
                "connection": {
                    "auth_url": s3_url,
                    "user_name": s3_access_key_id,
                    "password": s3_secret_access_key
                }
            }
        ],
        "framework": {
            "name": training_job_framework_name,
            "version": training_job_framework_version,
            "command": training_job_command
        },
        "evaluation_metrics": {
            "type": training_job_metric_type,
            "in": training_job_metric_path
        }
    }

    ''' Download FfDL CLI for log streaming '''
    res = requests.get('https://github.com/IBM/FfDL/raw/master/cli/bin/ffdl-linux', allow_redirects=True)
    open('ffdl', 'wb').write(res.content)
    subprocess.call(['chmod', '755', 'ffdl'])

    ''' Download the training model definition and FfDL manifest '''

    client = boto3.resource(
        's3',
        endpoint_url=s3_url,
        aws_access_key_id=s3_access_key_id,
        aws_secret_access_key=s3_secret_access_key,
    )

    try:
        client.Bucket(data_bucket_name).download_file(model_def_file_path, 'model.zip')
        if manifest_file_path:
            client.Bucket(data_bucket_name).download_file(manifest_file_path, 'manifest.yml')
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("The object does not exist.")
        else:
            raise

    ''' Update FfDL manifest with the corresponding object storage credentials '''
    if manifest_file_path:
        f = open('manifest.yml', 'r')
        manifest = yaml.load(f.read())
        f.close()
    else:
        manifest = ffdl_template

    manifest['data_stores'][0]['connection']['auth_url'] = s3_url
    manifest['data_stores'][0]['connection']['user_name'] = s3_access_key_id
    manifest['data_stores'][0]['connection']['password'] = s3_secret_access_key
    manifest['data_stores'][0]['training_data']['container'] = data_bucket_name
    manifest['data_stores'][0]['training_results']['container'] = result_bucket_name

    f = open('manifest.yml', 'w')
    yaml.default_flow_style = False
    yaml.dump(manifest, f)
    f.close()

    ''' Submit Training job to FfDL and monitor its status '''

    files = {
        'manifest': open('manifest.yml', 'rb'),
        'model_definition': open('model.zip', 'rb')
    }

    headers = {
        'accept': 'application/json',
        'Authorization': 'test',
        'X-Watson-Userinfo': 'bluemix-instance-id=test-user'
    }

    response = requests.post(ffdl_rest + '/v1/models?version=2017-02-13', files=files, headers=headers)
    print(response.json())
    id = response.json()['model_id']

    print('Training job has started, please visit the FfDL UI for more details')

    training_status = 'PENDING'
    os.environ['DLAAS_PASSWORD'] = 'test'
    os.environ['DLAAS_USERNAME'] = 'test-user'
    os.environ['DLAAS_URL'] = ffdl_rest

    while training_status != 'COMPLETED':
        response = requests.get(ffdl_rest + '/v1/models/' + id + '?version=2017-02-13', headers=headers)
        training_status = response.json()['training']['training_status']['status']
        print('Training Status: ' + training_status)
        if training_status == 'COMPLETED':
            with open('/tmp/training_id.txt', "w") as report:
                report.write(json.dumps(id))
            exit(0)
        if training_status == 'FAILED':
            print('Training failed. Exiting...')
            exit(1)
        if training_status == 'PROCESSING':
            counter = 0
            process = subprocess.Popen(['./ffdl', 'logs', id, '--follow'], stdout=subprocess.PIPE)
            while True:
                output = process.stdout.readline()
                if output:
                    print(output.strip())
                elif process.poll() is not None:
                    break
                else:
                    counter += 1
                    time.sleep(5)
                    if counter > 5:
                        break
        time.sleep(10)
