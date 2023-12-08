terraform {
  backend "s3" {
    bucket = "mcswain-dev-tf-states"
    key    = "ses-email-service"
    region = "us-east-1"
  }
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "5.30.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "2.4.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

resource "aws_cloudwatch_log_group" "email_blocklist" {
  name              = "/aws/lambda/${var.lambda_function_name}"
  retention_in_days = 14
}

resource "aws_sns_topic" "email_issues_sns" {
  name = var.lambda_function_name
}

resource "aws_sns_topic_subscription" "email_issues_to_lambda" {
  topic_arn = aws_sns_topic.email_issues_sns.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.email_blocklist.arn
}

resource "aws_lambda_permission" "aws_lambda_sns" {
  statement_id  = "AllowExecutionFromSNS"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.email_blocklist.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.email_issues_sns.arn
}

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "../../src-lambda"
  output_path = "lambda.zip"
}

resource "aws_lambda_function" "email_blocklist" {
  filename      = "lambda.zip"
  function_name = var.lambda_function_name
  role          = aws_iam_role.email_blocklist.arn
  handler       = "email_blocklist.lambda_handler"

  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  runtime = "python3.8"

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.email_blocklist.name
      EMAIL_FROM     = var.email_blocklist_failure_from_address
      EMAIL_TO       = var.email_blocklist_failure_to_address
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.email_blocklist,
  ]
}
