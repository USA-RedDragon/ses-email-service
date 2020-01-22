import asyncore
import base64
import concurrent.futures
import os
import smtpd
import smtplib
from smtplib import SMTPResponseException
import ssl

import boto3
from ratelimit import limits, sleep_and_retry

_DEFAULT_CIPHERS = (
    'ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:ECDH+HIGH:'
    'DH+HIGH:ECDH+3DES:DH+3DES:RSA+AESGCM:RSA+AES:RSA+HIGH:RSA+3DES:!aNULL:'
    '!eNULL:!MD5'
)

SES_RATE_LIMIT = int(os.getenv('SES_RATE_LIMIT', '10'))

DYNAMODB_TABLE = os.getenv('DYNAMODB_TABLE', '')

USE_APIKEY = os.getenv('USE_APIKEY', 'false').lower() == 'true'

if USE_APIKEY:
    DYNAMODB_API_KEYS_TABLE = os.getenv('DYNAMODB_API_KEYS_TABLE', '')

SMTP_HOST = os.getenv('SMTP_HOST', '0.0.0.0')
SMTP_PORT = int(os.getenv('SMTP_PORT', '1025'))

AWS_SMTP_HOST = os.getenv('AWS_SMTP_HOST', '0.0.0.0')
AWS_SMTP_PORT = int(os.getenv('AWS_SMTP_PORT', '1025'))
AWS_SMTP_USERNAME = os.getenv('AWS_SMTP_USERNAME', '')
AWS_SMTP_PASSWORD = os.getenv('AWS_SMTP_PASSWORD', '')

ENABLE_SSL = os.getenv('ENABLE_SSL', 'false').lower() == 'true'
SERVER_FQDN = os.getenv('SERVER_FQDN', '')
SSL_CERT_PATH = os.getenv('SSL_CERT_PATH', '/ssl/tls.crt')
SSL_KEY_PATH = os.getenv('SSL_KEY_PATH', '/ssl/tls.key')

USE_BLACKLIST = os.getenv('USE_BLACKLIST', 'false').lower() == 'true'

if USE_BLACKLIST or USE_APIKEY:
    dynamodb = boto3.client('dynamodb')


def decode_b64(data):
    """Wrapper for b64decode, without having to struggle with bytestrings."""
    byte_string = data.encode('utf-8')
    decoded = base64.b64decode(byte_string)
    return decoded.decode('utf-8')


def encode_b64(data):
    """Wrapper for b64encode, without having to struggle with bytestrings."""
    byte_string = data.encode('utf-8')
    encoded = base64.b64encode(byte_string)
    return encoded.decode('utf-8')


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


class SMTPChannel(smtpd.SMTPChannel):
    def __init__(self, server, conn, addr, *args, **kwargs):
        super().__init__(server, conn, addr, *args, **kwargs)
        self.username = None
        self.password = None
        self.authenticated = False
        self.authenticating = False
        self.credential_instance = None

    @property
    def credential_validator(self):
        return self.smtp_server.credential_validator

    def validate_credential(self, user, password):
        self.credential_instance = self.credential_validator(user, password, self.smtp_server)
        return self.credential_instance.validate()

    @property
    def allow_args_before_auth(self):
        return ['AUTH', 'EHLO', 'HELO', 'NOOP', 'RSET', 'QUIT']

    def run_command_with_arg(self, command, arg):
        method = getattr(self, 'smtp_' + command, None)
        if not method:
            self.push('500 Error: command "%s" not recognized' % command)
            return

        # White list of operations that are allowed prior to AUTH.
        if command not in self.allow_args_before_auth:
            if not self.authenticated:
                self.push('530 Authentication required')
                return

        method(arg)

    def smtp_EHLO(self, arg):
        if not arg:
            self.push('501 Syntax: HELO hostname')
        elif self.__greeting:
            self.push('503 Duplicate HELO/EHLO')
        else:
            self.__greeting = arg
            if isinstance(self.__conn, ssl.SSLSocket):
                self.push(f'250 {SERVER_FQDN}')

    def smtp_AUTH(self, arg):
        if 'PLAIN' in arg:
            split_args = arg.split(' ')
            # second arg is Base64-encoded string of blah\0username\0password
            authbits = decode_b64(split_args[1]).split('\0')
            self.username = authbits[1]
            self.password = authbits[2]
            if self.validate_credential(self.username, self.password):
                self.authenticated = True
                self.push('235 Authentication successful.')
            else:
                self.push('454 Temporary authentication failure.')
                self.close_when_done()

        elif 'LOGIN' in arg:
            self.authenticating = True
            split_args = arg.split(' ')

            # Some implmentations of 'LOGIN' seem to provide the username
            # along with the 'LOGIN' stanza, hence both situations are
            # handled.
            if len(split_args) == 2:
                self.username = decode_b64(arg.split(' ')[1])
                self.push('334 ' + encode_b64('Username'))
            else:
                self.push('334 ' + encode_b64('Username'))

        elif not self.username:
            self.username = decode_b64(arg)
            self.push('334 ' + encode_b64('Password'))
        else:
            self.authenticating = False
            self.password = decode_b64(arg)
            if self.validate_credential(self.username, self.password):
                self.authenticated = True
                self.push('235 Authentication successful.')
            else:
                self.push('454 Temporary authentication failure.')
                self.close_when_done()


class EmailRelayServer(smtpd.SMTPServer):
    def __init__(self, localaddr, remoteaddr, ssl_ctx=None):
        if ENABLE_SSL:
            self.ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            self.ssl_ctx.load_cert_chain(
                certfile=SSL_CERT_PATH,
                keyfile=SSL_KEY_PATH
            )
        super().__init__(self, localaddr, remoteaddr)
        print('TLS Mode: %s' % ('implicit' if ENABLE_SSL else 'disabled'), file=smtpd.DEBUGSTREAM)
        if ENABLE_SSL:
            print(f'TLS Context: {repr(self.ssl_ctx)}', file=smtpd.DEBUGSTREAM)

    def handle_accept(self):
        pair = self.accept()
        if pair is not None:
            conn, addr = pair
            print(f'Incoming connection from {addr}', file=smtpd.DEBUGSTREAM)
            if ENABLE_SSL and self.ssl_ctx:
                conn = self.ssl_ctx.wrap_socket(conn, server_side=True)
                print(f'Peer: {repr(addr)} - negotiated TLS: {repr(conn.cipher())}', file=smtpd.DEBUGSTREAM)
            channel = SMTPChannel(self, conn, addr)

    def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):
        print('#'*80, file=smtpd.DEBUGSTREAM)
        print(f'Receiving message from: {peer}', file=smtpd.DEBUGSTREAM)
        print(f'Message addressed from: {mailfrom}', file=smtpd.DEBUGSTREAM)
        print(f'Message addressed to  : {rcpttos}', file=smtpd.DEBUGSTREAM)
        print(f'Message length        : {len(data)}', file=smtpd.DEBUGSTREAM)
        print('#'*80, file=smtpd.DEBUGSTREAM)
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
                print('Not sending because STARTTLS is not enabled', file=smtpd.DEBUGSTREAM)
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
                print(f'SMTP Error while relaying email to SES: {str(e)}', file=smtpd.DEBUGSTREAM)
                server.quit()
                return f'{e.smtp_code} {e.smtp_error.decode()}'
            except Exception as e:
                print(f'Error relaying email to SES: {str(e)}', file=smtpd.DEBUGSTREAM)
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
                    f'Removing {email} from recipients due to being blacklisted',
                    file=smtpd.DEBUGSTREAM
                )
            else:
                new_addresses.append(email)
        return new_addresses
    else:
        return email_addresses


def main():
    print(f'Email server listing on {SMTP_HOST}:{SMTP_PORT}', file=smtpd.DEBUGSTREAM)
    EmailRelayServer((SMTP_HOST, SMTP_PORT), None)
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
