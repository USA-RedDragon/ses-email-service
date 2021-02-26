import os


# Rate Limit
SES_RATE_LIMIT = int(os.getenv('SES_RATE_LIMIT', '10'))

# Listener
SMTP_HOST = os.getenv('SMTP_HOST', '0.0.0.0')
SMTP_PORT = int(os.getenv('SMTP_PORT', '465'))

# Endpoint
AWS_SMTP_HOST = os.getenv('AWS_SMTP_HOST', '0.0.0.0')
AWS_SMTP_PORT = int(os.getenv('AWS_SMTP_PORT', '587'))
AWS_SMTP_USERNAME = os.getenv('AWS_SMTP_USERNAME', '')
AWS_SMTP_PASSWORD = os.getenv('AWS_SMTP_PASSWORD', '')

# API Key Auth
USE_APIKEY = os.getenv('USE_APIKEY', 'false').lower() == 'true'
DYNAMODB_API_KEYS_TABLE = os.getenv('DYNAMODB_API_KEYS_TABLE', '')

# SSL
SERVER_FQDN = os.getenv('SERVER_FQDN', '')
ENABLE_SSL = os.getenv('ENABLE_SSL', 'false').lower() == 'true'
SSL_CERT_PATH = os.getenv('SSL_CERT_PATH', '/ssl/tls.crt')
SSL_KEY_PATH = os.getenv('SSL_KEY_PATH', '/ssl/tls.key')

# Blacklist Stripping
USE_BLACKLIST = os.getenv('USE_BLACKLIST', 'false').lower() == 'true'
DYNAMODB_TABLE = os.getenv('DYNAMODB_TABLE', '')
