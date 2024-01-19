import concurrent.futures
import smtplib
import ssl
import sys

from aiosmtpd.smtp import AuthResult, LoginPassword
from ratelimit import limits, sleep_and_retry

from config import (
    USE_BLOCKLIST,
    SES_RATE_LIMIT,
    AWS_SMTP_HOST,
    AWS_SMTP_PASSWORD,
    AWS_SMTP_PORT,
    AWS_SMTP_USERNAME,
)

from db import remove_blocklist, validate_password

_DEFAULT_CIPHERS = (
    'ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:ECDH+HIGH:'
    'DH+HIGH:ECDH+3DES:DH+3DES:RSA+AESGCM:RSA+AES:RSA+HIGH:RSA+3DES:!aNULL:'
    '!eNULL:!MD5'
)

def authenticator(_server, _session, _envelope, mechanism, auth_data):
    fail_not_handled = AuthResult(success=False, handled=False)
    if mechanism not in ("LOGIN", "PLAIN"):
        return fail_not_handled
    if not isinstance(auth_data, LoginPassword):
        return fail_not_handled
    if not validate_password(auth_data.password.decode()):
        return fail_not_handled
    return AuthResult(success=True)

class SMTPHandler:
    async def handle_DATA(self, _server, session, envelope):
        print('#'*80, file=sys.stdout)
        print(f'Receiving message from: {session.peer}', file=sys.stdout)
        print(f'Message addressed from: {envelope.mail_from}', file=sys.stdout)
        print(f'Message addressed to  : {envelope.rcpt_tos}', file=sys.stdout)
        print(f'Message length        : {len(envelope.original_content)}', file=sys.stdout)
        print('#'*80, file=sys.stdout)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            return executor.submit(
                self._send_email,
                envelope.mail_from,
                envelope.rcpt_tos,
                envelope.original_content,
                envelope.mail_options,
                envelope.rcpt_options,
            ).result()

    @sleep_and_retry
    @limits(calls=SES_RATE_LIMIT, period=1)
    def _send_email(self, mail_from, rcpt_tos, data, mail_options, rcpt_options):
        with smtplib.SMTP(AWS_SMTP_HOST, AWS_SMTP_PORT) as server:
            context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            context.options |= ssl.OP_NO_SSLv2
            context.options |= ssl.OP_NO_SSLv3

            context.set_ciphers(_DEFAULT_CIPHERS)
            context.set_default_verify_paths()
            context.verify_mode = ssl.CERT_REQUIRED

            if server.starttls(context=context)[0] != 220:
                print(
                    'Not sending because STARTTLS is not enabled',
                    file=sys.stderr
                )
                # cancel if connection is not encrypted
                return '554 Transaction failed: STARTTLS is required'

            server.login(AWS_SMTP_USERNAME, AWS_SMTP_PASSWORD)

            try:
                if USE_BLOCKLIST:
                    # Filter out blocklisted email addresses
                    rcpt_tos = remove_blocklist(rcpt_tos)

                # Strip SMTPUTF8 from mail_options, if present
                mail_options = [m for m in mail_options if m != 'SMTPUTF8']

                send_errs = server.sendmail(
                    mail_from,
                    rcpt_tos,
                    data,
                    mail_options=mail_options,
                    rcpt_options=rcpt_options,
                )
                if send_errs:
                    print(
                        f'Error relaying email to SES: {send_errs}',
                        file=sys.stderr
                    )
                    server.quit()
                    return '554 Transaction failed'
                else:
                    server.quit()
                    return '250 Message accepted for delivery'
            except Exception as e:
                print(
                    f'SMTP Error while relaying email to SES: {str(e)}',
                    file=sys.stderr
                )
                server.quit()
                return f'554 Transaction failed'
