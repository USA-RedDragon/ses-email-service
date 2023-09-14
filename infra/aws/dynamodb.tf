
resource "aws_dynamodb_table" "email_blocklist" {
  name           = "${var.lambda_function_name}-blocklist"
  read_capacity  = 1
  write_capacity = 1
  hash_key       = "email"

  attribute {
    name = "email"
    type = "S"
  }

  tags = {
    Name = "${var.lambda_function_name}-blocklist"
  }
}

resource "aws_dynamodb_table" "api_keys" {
  name           = "${var.lambda_function_name}-api_keys"
  read_capacity  = 1
  write_capacity = 1
  hash_key       = "api_key"

  attribute {
    name = "api_key"
    type = "S"
  }

  tags = {
    Name = "${var.lambda_function_name}-api_keys"
  }
}
