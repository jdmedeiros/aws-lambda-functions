import json
import logging
import boto3
from botocore.exceptions import ClientError
from types import SimpleNamespace


class BetterNamespace(SimpleNamespace):
    def __getitem__(self, key):
        return getattr(self, key)


def send_sqs_message(QueueName, msg_body):
    sqs_client = boto3.client('sqs')
    sqs_queue_url = sqs_client.get_queue_url(QueueName=QueueName)['QueueUrl']
    try:
        msg = sqs_client.send_message(QueueUrl=sqs_queue_url, MessageBody=msg_body)
    except ClientError as e:
        logging.error(e)
        return None
    return msg


def lambda_handler(event, context):
    QueueName = 'aws-emr-control'
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(asctime)s: %(message)s')
    from_users = ('user.one@domain.com', 'user.two@domain.com', 'user.three@domain.com')
    to_users = ('startstopemr@domain.com')
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
            if subject.action.lower() in ('start', 'stop', 'status'):
                message = record['ses']['mail']['commonHeaders']['subject']
            if subject.action.lower() in ('start', 'stop', 'status'):
                msg = send_sqs_message(QueueName, message)
                if msg is not None:
                    logging.info(f'Sent SQS message ID: {msg["MessageId"]}')
                return {
                    'statusCode': 200,
                    'body': json.dumps(msg)
                }
            else:
                print(f'ERROR: Invalid action')
            print(subject)
        else:
            print('ERROR - Invalid email message')
            print(record)
