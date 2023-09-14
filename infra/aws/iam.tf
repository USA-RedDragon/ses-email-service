
resource "aws_iam_role" "email_blocklist" {
  name = var.lambda_function_name

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow"
    },
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "sns.amazonaws.com"
      },
      "Effect": "Allow"
    }
  ]
}
EOF
}

resource "aws_iam_policy" "email_blocklist" {
  name        = var.lambda_function_name
  path        = "/"
  description = "IAM policy for lambda email blocklist"

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "${aws_cloudwatch_log_group.email_blocklist.arn}",
      "Effect": "Allow"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ses:SendEmail",
        "ses:SendRawEmail"
      ],
      "Resource": [
        "${var.ses_identity_arn}"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "sns:ConfirmSubscription",
        "sns:Subscribe",
        "sns:Unsubscribe"
      ],
      "Resource": [
        "${aws_sns_topic.email_issues_sns.arn}"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem"
      ],
      "Resource": "${aws_dynamodb_table.email_blocklist.arn}"
    }
  ]
}
EOF
}

resource "aws_iam_policy" "email_service" {
  name        = "${var.lambda_function_name}-email-service"
  path        = "/"
  description = "IAM policy for email service"

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ses:SendRawEmail"
      ],
      "Resource": [
        "${var.ses_identity_arn}"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem"
      ],
      "Resource": [
        "${aws_dynamodb_table.email_blocklist.arn}",
        "${aws_dynamodb_table.api_keys.arn}"
      ]
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "email_blocklist" {
  role       = aws_iam_role.email_blocklist.name
  policy_arn = aws_iam_policy.email_blocklist.arn
}

resource "aws_iam_user" "email_service" {
  name = "${var.lambda_function_name}-email_service"
}

resource "aws_iam_user_policy_attachment" "email_service" {
  user       = aws_iam_user.email_service.name
  policy_arn = aws_iam_policy.email_service.arn
}

resource "aws_iam_access_key" "email_service" {
  user = aws_iam_user.email_service.name
}
