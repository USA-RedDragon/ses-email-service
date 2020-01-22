# SES Email Service

[![Build Status](https://drone.liquidfish.xyz/api/badges/liquidfish/ses-email-service/status.svg)](https://drone.liquidfish.xyz/liquidfish/ses-email-service)
[![](https://images.microbadger.com/badges/image/liquidfish/ses-email-service.svg)](https://microbadger.com/images/liquidfish/ses-email-service "Get your own image badge on microbadger.com")

This service is used to help with clients who need a large amount of emails sent via SES and need to deal with rate limiting.

There are two services within this repo, the SES Email Service to be run as a Docker container, and the Email Blacklist service that runs in Lambda and listens to SNS for email bounce or complaint notifications, and adds them to a global blacklist.

The blacklist lambda will update automatically with a push to the master branch.

The email service docker will update `:latest` on a push to the master branch, and will update version `:x.x.x` if you tag a commit with a semver version tag, for example, Docker tag `:1.0.0` points to Git tag `1.0.0`.

## Service Environment Variables

|  Environment Variable   |                                                                       Details                                                                       |                     Example                     |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| `USE_BLACKLIST`         | Whether to use the Liquidfish email recipient blacklist                                                                                             | `true`                                          |
| `AWS_ACCESS_KEY_ID`     | Specifies an AWS access key associated with an IAM user or role, used to access the shared blacklist                                                | `AKIA0000000000000000`                          |
| `AWS_SECRET_ACCESS_KEY` | Specifies the secret key associated with the access key. This is essentially the "password" for the access key. Used to access the shared blacklist | `0000000000000000000000000000000000000`         |
| `AWS_DEFAULT_REGION`    | Specifies the AWS Region to send the request to. Used to access the shared blacklist                                                                | `us-east-1`                                     |
| `SES_RATE_LIMIT`        | Specifies the maximum emails per second you are allowed to send per second                                                                          | `10`                                            |
| `DYNAMODB_TABLE`        | DynamoDB table with the blacklist                                                                                                                   | `ses-blacklist`                                 |
| `SMTP_HOST`             | Specifies the host to listen on                                                                                                                     | `0.0.0.0`                                       |
| `SMTP_PORT`             | Specifies the port to listen on                                                                                                                     | `1025`                                          |
| `AWS_SMTP_HOST`         | Specifies the AWS SES SMTP host to talk to                                                                                                          | `email-smtp.us-east-1.amazonaws.com`            |
| `AWS_SMTP_PORT`         | Specifies the AWS SES SMTP port to talk to                                                                                                          | `587`                                           |
| `AWS_SMTP_USERNAME`     | Specifies the AWS SES SMTP username                                                                                                                 | `AKIA0000000000000000`                          |
| `AWS_SMTP_PASSWORD`     | Specifies the AWS SES SMTP username                                                                                                                 | `ABCDEF/GHIJKLMNOPQRSTUVWXYZABCDEFGHIJKLMNOPQR` |

## Lambda Environment Variables

| Environment Variable |                             Details                             |              Example               |
| -------------------- | --------------------------------------------------------------- | ---------------------------------- |
| `SES_REGION`         | The region that SES is working in                               | `us-east-1`                        |
| `EMAIL_FROM`         | The email address to send emails from                           | `backups@domain.com`               |
| `EMAIL_TO`           | The list of email addresses to send to, separated by semicolons | `user@domain.com;user1@domain.com` |
| `DYNAMODB_TABLE`     | DynamoDB table with the blacklist                               | `ses-blacklist`                    |

## IAM Roles

Here are the permissions required to run the Email Blacklist Lambda

### Email Blacklist Lambda

Here are the permissions required to run the Email Blacklist Lambda

#### Email Blacklist Policy

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

#### Email Blacklist Trust Relationship

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

### Email Blacklist DynamoDB Access

Here are the permissions required to access the Email Blacklist from the SES Service (BLACKLIST_AWS_ACCESS_KEY_ID and adjacent environment variables)

#### Email Blacklist DynamoDB Policy

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": "dynamodb:GetItem",
            "Resource": "arn:aws:dynamodb:<REGION>:<ACCOUNT_ID>:table/<TABLE_NAME>"
        }
    ]
}
```
