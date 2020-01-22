import asyncore
import concurrent.futures
import smtpd
import smtplib
from smtplib import SMTPResponseException
import ssl

import boto3
from ratelimit import limits, sleep_and_retry

from config import (
    ENABLE_SSL,
    USE_BLACKLIST,
    SSL_CERT_PATH,
    SSL_KEY_PATH,
    SES_RATE_LIMIT,
    AWS_SMTP_HOST,
    AWS_SMTP_PASSWORD,
    AWS_SMTP_PORT,
    AWS_SMTP_USERNAME,
    SMTP_HOST,
    SMTP_PORT,
    DYNAMODB_TABLE,
)

from smtpchannel import SMTPChannel


_DEFAULT_CIPHERS = (
    'ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:ECDH+HIGH:'
    'DH+HIGH:ECDH+3DES:DH+3DES:RSA+AESGCM:RSA+AES:RSA+HIGH:RSA+3DES:!aNULL:'
    '!eNULL:!MD5'
)

if USE_BLACKLIST:
    dynamodb = boto3.client('dynamodb')


class EmailRelayServer(smtpd.SMTPServer):
    channel_class = SMTPChannel

    def __init__(self, localaddr, remoteaddr, ssl_ctx=None):
        if ENABLE_SSL:
            self.ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            self.ssl_ctx.load_cert_chain(
                certfile=SSL_CERT_PATH,
                keyfile=SSL_KEY_PATH
            )
        smtpd.SMTPServer.__init__(self, localaddr, remoteaddr)
        print(
            'TLS Mode: %s' % ('implicit' if ENABLE_SSL else 'disabled'),
            file=smtpd.DEBUGSTREAM
        )
        if ENABLE_SSL:
            print(f'TLS Context: {repr(self.ssl_ctx)}', file=smtpd.DEBUGSTREAM)

    def handle_accept(self):
        pair = self.accept()
        if pair is not None:
            conn, addr = pair
            print(f'Incoming connection from {addr}', file=smtpd.DEBUGSTREAM)
            if ENABLE_SSL and self.ssl_ctx:
                conn = self.ssl_ctx.wrap_socket(conn, server_side=True)
                print(
                    f'Peer: {repr(addr)} - TLS: {repr(conn.cipher())}',
                    file=smtpd.DEBUGSTREAM
                )
            self.channel = SMTPChannel(self, conn, addr)

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
                print(
                    'Not sending because STARTTLS is not enabled',
                    file=smtpd.DEBUGSTREAM
                )
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
                print(
                    f'SMTP Error while relaying email to SES: {str(e)}',
                    file=smtpd.DEBUGSTREAM
                )
                server.quit()
                return f'{e.smtp_code} {e.smtp_error.decode()}'
            except Exception as e:
                print(
                    f'Error relaying email to SES: {str(e)}',
                    file=smtpd.DEBUGSTREAM
                )
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
                    f'Removing {email} due to being blacklisted',
                    file=smtpd.DEBUGSTREAM
                )
            else:
                new_addresses.append(email)
        return new_addresses
    else:
        return email_addresses


def main():
    print(
        f'Email server listing on {SMTP_HOST}:{SMTP_PORT}'
    )
    EmailRelayServer((SMTP_HOST, SMTP_PORT), None)
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
