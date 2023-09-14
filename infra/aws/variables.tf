variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "lambda_function_name" {
  type    = string
  default = "email-blocklist"
}

variable "ses_identity_arn" {
  type = string
}

variable "email_blocklist_failure_from_address" {
  type = string
}

variable "email_blocklist_failure_to_address" {
  type = string
}
