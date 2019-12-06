import json
import os
import traceback

import boto3

EMAIL_FROM = os.getenv('EMAIL_FROM', '')
EMAIL_TO = os.getenv('EMAIL_TO', '').split(';')
SES_REGION = os.getenv('SES_REGION', 'us-east-1')

dynamodb = boto3.client('dynamodb')


def exit(error=None):
    if error is not None:
        print('Error occurred, sending email...')
        print(error)
        email(error, EMAIL_FROM, EMAIL_TO)


def email(error, from_address, addresses):
    try:
        ses = boto3.client('ses', region_name=SES_REGION)
        errString = ''.join(traceback.format_exception(etype=type(error), value=error, tb=error.__traceback__))
        ses.send_email(
            Source=from_address,
            Destination={
                'ToAddresses': addresses
            },
            Message={
                'Subject': {
                    'Data': 'SES Error: Email Blacklist Failed'
                },
                'Body': {
                    'Text': {
                        'Data': f'Failed to add emails to blacklist:\n{errString}'
                    }
                }
            }
        )
    except Exception as e:
        print('Error sending email...')
        print(e)


def lambda_handler(event, context):
    try:
        for record in event['Records']:
            sns_message = json.loads(record['Sns']['Message'])
            if sns_message['notificationType'] == 'Bounce' and sns_message['bounce']['bounceType'] == 'Permanent':
                for bounced_recipient in sns_message['bounce']['bouncedRecipients']:
                    email = bounced_recipient['emailAddress']
                    dynamodb.put_item(
                        Item={
                            'email': {
                                'S': email,
                            },
                        },
                        TableName='ses_blacklist',
                    )
                    print(f'{email} is a bounced email recipient, blacklisting')
            elif sns_message['notificationType'] == 'Bounce' and sns_message['bounce']['bounceType'] == 'Transient':
                for bounced_recipient in sns_message['bounce']['bouncedRecipients']:
                    email = bounced_recipient['emailAddress']
                    print(f'{email} is a transient bounced email recipient, not blacklisting')
            else:
                print('No clue what\'s going on right now.....')

        return {
            'statusCode': 200
        }
    except Exception as e:
        exit(e)
        return {
            'statusCode': 500
        }
