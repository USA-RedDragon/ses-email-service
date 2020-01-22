import boto3

from config import DYNAMODB_API_KEYS_TABLE, USE_APIKEY


if USE_APIKEY:
    dynamodb = boto3.client('dynamodb')


class CredentialValidator(object):
    def __init__(self, username, password, smtp_server):
        self.password = password

    def validate(self):
        item = dynamodb.get_item(
            Key={
                'api_key': {
                    'S': self.password,
                },
            },
            TableName=DYNAMODB_API_KEYS_TABLE,
        )
        return True if 'Item' in item.keys() else False
