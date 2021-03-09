output "email_service_smtp_password" {
  value     = aws_iam_access_key.email_service.ses_smtp_password_v4
  sensitive = true
}

output "email_service_access_key" {
  value = aws_iam_access_key.email_service.id
}

output "email_service_secret_key" {
  value     = aws_iam_access_key.email_service.secret
  sensitive = true
}

output "dynamodb_table_blacklist" {
  value = aws_dynamodb_table.email_blacklist.name
}

output "dynamodb_table_api_keys" {
  value = aws_dynamodb_table.api_keys.name
}
