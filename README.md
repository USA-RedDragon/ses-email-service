# SES Email Service

[![Blocklist Lambda](https://github.com/USA-RedDragon/ses-email-service/actions/workflows/email-blocklist.yaml/badge.svg?branch=main)](https://github.com/USA-RedDragon/ses-email-service/actions/workflows/email-blocklist.yaml)
[![Docker Images](https://github.com/USA-RedDragon/ses-email-service/actions/workflows/email-service.yaml/badge.svg?branch=main)](https://github.com/USA-RedDragon/ses-email-service/actions/workflows/email-service.yaml)

This service is used to help with clients who need a large amount of emails sent via SES and need to deal with rate limiting.

There are two services within this repo, the SES Email Service to be run as a Docker container, and the Email Blocklist service that runs in Lambda and listens to SNS for email bounce or complaint notifications, and adds them to a global blocklist.

The blocklist lambda will update automatically with a push to the main branch.

The email service docker will update `:latest` on a push to the main branch

## Service Environment Variables

|   Environment Variable    |                                                                       Details                                                                       |                     Example                     |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| `USE_BLOCKLIST`           | Whether to use the email recipient blocklist                                                                                                        | `true`                                          |
| `AWS_ACCESS_KEY_ID`       | Specifies an AWS access key associated with an IAM user or role, used to access the shared blocklist                                                | `AKIA0000000000000000`                          |
| `AWS_SECRET_ACCESS_KEY`   | Specifies the secret key associated with the access key. This is essentially the "password" for the access key. Used to access the shared blocklist | `0000000000000000000000000000000000000`         |
| `AWS_DEFAULT_REGION`      | Specifies the AWS Region to send the request to. Used to access the shared blocklist                                                                | `us-east-1`                                     |
| `SES_RATE_LIMIT`          | Specifies the maximum emails per second you are allowed to send per second                                                                          | `10`                                            |
| `DYNAMODB_TABLE`          | DynamoDB table with the blocklist                                                                                                                   | `ses-blocklist`                                 |
| `DYNAMODB_API_KEYS_TABLE` | DynamoDB table with api keys                                                                                                                        | `ses-api-keys`                                  |
| `SMTP_HOST`               | Specifies the host to listen on                                                                                                                     | `0.0.0.0`                                       |
| `SMTP_PORT`               | Specifies the port to listen on                                                                                                                     | `465`                                          |
| `AWS_SMTP_HOST`           | Specifies the AWS SES SMTP host to talk to                                                                                                          | `email-smtp.us-east-1.amazonaws.com`            |
| `AWS_SMTP_PORT`           | Specifies the AWS SES SMTP port to talk to                                                                                                          | `587`                                           |
| `AWS_SMTP_USERNAME`       | Specifies the AWS SES SMTP username                                                                                                                 | `AKIA0000000000000000`                          |
| `AWS_SMTP_PASSWORD`       | Specifies the AWS SES SMTP username                                                                                                                 | `ABCDEF/GHIJKLMNOPQRSTUVWXYZABCDEFGHIJKLMNOPQR` |
| `SERVER_FQDN`             | Specifies server domain name, for certificate verification                                                                                          | `email.example.com`                             |
| `ENABLE_SSL`              | Whether to use ssl                                                                                                                                  | `true`                                          |
| `SSL_CERT_PATH`           | Specifies the SSL certificate path                                                                                                                  | `/ssl/tls.crt`                                  |
| `SSL_KEY_PATH`            | Specifies the SSL private key path                                                                                                                  | `/ssl/tls.key`                                  |

## Lambda Environment Variables

| Environment Variable |                             Details                             |              Example               |
| -------------------- | --------------------------------------------------------------- | ---------------------------------- |
| `SES_REGION`         | The region that SES is working in                               | `us-east-1`                        |
| `EMAIL_FROM`         | The email address to send emails from                           | `backups@domain.com`               |
| `EMAIL_TO`           | The list of email addresses to send to, separated by semicolons | `user@domain.com;user1@domain.com` |
| `DYNAMODB_TABLE`     | DynamoDB table with the blocklist                               | `ses-blocklist`                    |

## IAM Roles

Here are the permissions required to run the Email Blocklist Lambda

### Email Blocklist Lambda

Here are the permissions required to run the Email Blocklist Lambda

#### Email Blocklist Policy

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "ses:SendEmail",
                "ses:SendRawEmail"
            ],
            "Resource": [
                "arn:aws:ses:<REGION>:<ACCOUNT_ID>:identity/<SES_DOMAIN>"
            ]
        },
        {
            "Sid": "VisualEditor1",
            "Effect": "Allow",
            "Action": [
                "sns:ConfirmSubscription",
                "sns:Subscribe",
                "sns:Unsubscribe"
            ],
            "Resource": [
                "arn:aws:sns:<REGION>:<ACCOUNT_ID>:<SNS_TOPIC_NAME>"
            ]
        },
        {
            "Sid": "VisualEditor2",
            "Effect": "Allow",
            "Action": [
                "dynamodb:PutItem"
            ],
            "Resource": "arn:aws:dynamodb:<REGION>:<ACCOUNT_ID>:table/<DYNAMODB_TABLE_NAME>"
        }
    ]
}
```

#### Email Blocklist Trust Relationship

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    },
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "sns.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

### Email Blocklist DynamoDB Access

Here are the permissions required to access the Email Blocklist from the SES Service (AWS_ACCESS_KEY_ID and adjacent environment variables)

#### Email Blocklist DynamoDB Policy

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": "dynamodb:GetItem",
            "Resource": [
                "arn:aws:dynamodb:<REGION>:<ACCOUNT_ID>:table/<BLOCKLIST_TABLE_NAME>",
                "arn:aws:dynamodb:<REGION>:<ACCOUNT_ID>:table/<API_KEY_TABLE_NAME>"
            ]
        }
    ]
}
```
