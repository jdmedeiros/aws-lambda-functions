import json
import logging
import boto3
from botocore.exceptions import ClientError
from types import SimpleNamespace


class BetterNamespace(SimpleNamespace):
    def __getitem__(self, key):
        return getattr(self, key)


def start_instances(instance_name):
    region = 'us-east-1'
    ec2 = boto3.client('ec2', 'us-east-1')
    instances = [i for i in boto3.resource('ec2', region_name=region).instances.all()]
    startlist = []
    for i in instances:
        if i.tags is not None and 'Name' in [t['Key'] for t in i.tags]:
            for t in i.tags:
                if t['Key']=="Name" and t['Value']==instance_name:
                    if i.state['Name'] == 'stopped':
                        startlist.append(i.instance_id)
    if len(startlist) > 0:
        print(f'startlist={startlist}')
        response = ec2.start_instances(InstanceIds=startlist)
        print(f'response={response}')
    else:
        print(json.dumps('None of the instances qualified to be started.'))


def stop_instances(instance_name):
    region = 'us-east-1'
    ec2 = boto3.client('ec2', 'us-east-1')
    instances = [i for i in boto3.resource('ec2', region_name=region).instances.all()]
    stoplist = []
    for i in instances:
        if i.tags is not None and 'Name' in [t['Key'] for t in i.tags]:
            for t in i.tags:
                if t['Key']=="Name" and t['Value']==instance_name:
                    if i.state['Name'] == 'running' and not i.spot_instance_request_id:
                        stoplist.append(i.instance_id)
    if len(stoplist) > 0:
        print(f'stoplist={stoplist}')
        response = ec2.stop_instances(InstanceIds=stoplist)
        print(f'response={response}')
    else:
        print(json.dumps('None of the instances qualified to be stopped.'))


def lambda_handler(event, context):
    QueueName = 'aws-ec2-control'
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(asctime)s: %(message)s')
    from_users = ('user.one@domain.com', 'user.two@domain.com', 'user.three@domain.com')
    to_users = ('startstopone@domain.com')
    valids = []
    for record in event['Records']:
        valid_dest = 'FAIL'
        for destination in record['ses']['mail']['destination']:
            if destination in to_users:
                valid_dest = 'PASS'
        valids.append(valid_dest)

        if record['ses']['mail']['source'] in from_users:
            valids.append('PASS')
        else:
            valids.append('FAIL')

        valids.append(record['ses']['receipt']['spamVerdict']['status'])
        valids.append(record['ses']['receipt']['virusVerdict']['status'])
        valids.append(record['ses']['receipt']['spfVerdict']['status'])
        valids.append(record['ses']['receipt']['dkimVerdict']['status'])
        valids.append(record['ses']['receipt']['dmarcVerdict']['status'])

        if all(valid == 'PASS' for valid in valids):
            subject = json.loads(record['ses']['mail']['commonHeaders']['subject'],
                                 object_hook=lambda d: SimpleNamespace(**d))
            if subject.action.lower() == 'start' or subject.action.lower() == 'stop':
                if subject.action.lower() == 'start':
                    start_instances(subject.instance_name)
                else:
                    stop_instances(subject.instance_name)
                return {
                    'statusCode': 200
                }
            else:
                print(f'ERROR: Invalid action')
            print(subject)
        else:
            print('ERROR - Invalid email message')
            print(record)
