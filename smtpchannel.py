import smtpd
import ssl

from utils import decode_b64, encode_b64
from config import SERVER_FQDN


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
        self.credential_instance = self.credential_validator(
            user,
            password,
            self.smtp_server
        )
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
