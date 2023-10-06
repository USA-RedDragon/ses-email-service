import sys

import boto3

from config import (
    DYNAMODB_API_KEYS_TABLE,
    DYNAMODB_TABLE,
    USE_BLOCKLIST,
)

dynamodb = boto3.client('dynamodb')

def validate_password(password):
    try:
        item = boto3.client('dynamodb').get_item(
            Key={
                'api_key': {
                    'S': password,
                },
            },
            TableName=DYNAMODB_API_KEYS_TABLE,
        )
        return True if 'Item' in item.keys() else False
    except Exception as e:
        print(
            f'Error validating API key: {str(e)}',
            file=sys.stderr
        )
        return False

def remove_blocklist(email_addresses):
    if USE_BLOCKLIST:
        new_addresses = []
        for email in email_addresses:
            item = dynamodb.get_item(
                Key={
                    'email': {
                        'S': email,
                    },
                },
                TableName=DYNAMODB_TABLE,
            )
            if 'Item' in item.keys():
                print(
                    f'Removing {email} due to being blocklisted',
                    file=sys.stdout
                )
            else:
                new_addresses.append(email)
        return new_addresses
    else:
        return email_addresses
