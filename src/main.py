import asyncio
import ssl
import sys

from aiosmtpd.controller import Controller

from config import (
    ENABLE_SSL,
    SSL_CERT_PATH,
    SSL_KEY_PATH,
    SMTP_HOST,
    SMTP_PORT,
)
from server import SMTPHandler, authenticator

def create_ssl_context():
    context = None
    if ENABLE_SSL:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(
            certfile=SSL_CERT_PATH,
            keyfile=SSL_KEY_PATH
        )
    print(
        'TLS Mode: %s' % ('implicit' if ENABLE_SSL else 'disabled'),
        file=sys.stdout
    )
    return context


async def main():
    print('ses-email-service', file=sys.stdout)
    print(f"Listening on port {SMTP_PORT}", file=sys.stdout)
    controller = Controller(
        SMTPHandler(),
        hostname="",
        port=SMTP_PORT,
        server_hostname=SMTP_HOST,
        ssl_context=create_ssl_context(),
        authenticator=authenticator,
        auth_required=True,
        # needed until https://github.com/aio-libs/aiosmtpd/issues/281 is fixed
        auth_require_tls=False)
    controller.start()

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(main())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("Shutting down...")
