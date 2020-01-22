import asyncore
import concurrent.futures
import os
from smtpd import SMTPServer
import smtplib
from smtplib import SMTPResponseException
import ssl

import boto3
from ratelimit import limits, sleep_and_retry

DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'

_DEFAULT_CIPHERS = (
    'ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:ECDH+HIGH:'
    'DH+HIGH:ECDH+3DES:DH+3DES:RSA+AESGCM:RSA+AES:RSA+HIGH:RSA+3DES:!aNULL:'
    '!eNULL:!MD5'
)

SES_RATE_LIMIT = int(os.getenv('SES_RATE_LIMIT', '10'))

DYNAMODB_TABLE = os.getenv('DYNAMODB_TABLE', '')
DYNAMODB_API_KEYS_TABLE = os.getenv('DYNAMODB_API_KEYS_TABLE', '')

SMTP_HOST = os.getenv('SMTP_HOST', '0.0.0.0')
SMTP_PORT = int(os.getenv('SMTP_PORT', '1025'))

AWS_SMTP_HOST = os.getenv('AWS_SMTP_HOST', '0.0.0.0')
AWS_SMTP_PORT = int(os.getenv('AWS_SMTP_PORT', '1025'))
AWS_SMTP_USERNAME = os.getenv('AWS_SMTP_USERNAME', '')
AWS_SMTP_PASSWORD = os.getenv('AWS_SMTP_PASSWORD', '')

USE_BLACKLIST = os.getenv('USE_BLACKLIST', 'false').lower() == 'true'

if USE_BLACKLIST:
    dynamodb = boto3.client('dynamodb')


class EmailRelayServer(SMTPServer):
    def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):
        if DEBUG:
            print('#'*80)
            print(f'Receiving message from: {peer}')
            print(f'Message addressed from: {mailfrom}')
            print(f'Message addressed to  : {rcpttos}')
            print(f'Message length        : {len(data)}')
            print('#'*80)
        return self.send_email(
            mailfrom,
            rcpttos,
            data,
            kwargs['mail_options'],
            kwargs['rcpt_options'],
        )

    def send_email(self, mailfrom, rcpttos, data, mail_options, rcpt_options):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            return executor.submit(
                self._send_email,
                mailfrom,
                rcpttos,
                data,
                mail_options,
                rcpt_options,
            ).result()

    @sleep_and_retry
    @limits(calls=SES_RATE_LIMIT, period=1)
    def _send_email(self, mailfrom, rcpttos, data, mail_options, rcpt_options):
        with smtplib.SMTP(AWS_SMTP_HOST, AWS_SMTP_PORT) as server:
            # only TLSv1 or higher
            context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            context.options |= ssl.OP_NO_SSLv2
            context.options |= ssl.OP_NO_SSLv3

            context.set_ciphers(_DEFAULT_CIPHERS)
            context.set_default_verify_paths()
            context.verify_mode = ssl.CERT_REQUIRED

            if server.starttls(context=context)[0] != 220:
                if DEBUG:
                    print('Not sending because STARTTLS is not enabled')
                # cancel if connection is not encrypted
                return '554 Transaction failed: STARTTLS is required'

            server.login(AWS_SMTP_USERNAME, AWS_SMTP_PASSWORD)

            try:
                if USE_BLACKLIST:
                    # Filter out blacklisted email addresses
                    rcpttos = removeBlacklist(rcpttos)

                server.sendmail(
                    mailfrom,
                    rcpttos,
                    data,
                    mail_options=mail_options,
                    rcpt_options=rcpt_options,
                )
            except SMTPResponseException as e:
                if DEBUG:
                    print(f'SMTP Error while relaying email to SES: {str(e)}')
                server.quit()
                return f'{e.smtp_code} {e.smtp_error.decode()}'
            except Exception as e:
                print(f'Error relaying email to SES: {str(e)}')
                server.quit()
                return f'554 Transaction failed: {str(e)}'


def removeBlacklist(email_addresses):
    if USE_BLACKLIST:
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
                    f'Removing {email} from recipients due to being blacklistd'
                )
            else:
                new_addresses.append(email)
        return new_addresses
    else:
        return email_addresses


def isAuthorized(api_key):
    item = dynamodb.get_item(
        Key={
            'api_key': {
                'S': api_key,
            },
        },
        TableName=DYNAMODB_API_KEYS_TABLE,
    )
    return True if 'Item' in item.keys() else False


def main():
    print(f'Email server listing on {SMTP_HOST}:{SMTP_PORT}')
    EmailRelayServer((SMTP_HOST, SMTP_PORT), None)
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
