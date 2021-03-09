
resource "aws_dynamodb_table" "email_blacklist" {
  name           = "${var.lambda_function_name}-blacklist"
  read_capacity  = 1
  write_capacity = 1
  hash_key       = "email"

  attribute {
    name = "email"
    type = "S"
  }

  tags = {
    Name = "${var.lambda_function_name}-blacklist"
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
