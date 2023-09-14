variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "lambda_function_name" {
  type    = string
  default = "email-blacklist"
}

variable "ses_identity_arn" {
  type = string
}

variable "email_blacklist_failure_from_address" {
  type = string
}

variable "email_blacklist_failure_to_address" {
  type = string
}
