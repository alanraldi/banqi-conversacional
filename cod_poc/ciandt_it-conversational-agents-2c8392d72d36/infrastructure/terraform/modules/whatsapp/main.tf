# -----------------------------------------------------------------------------
# WhatsApp Channel — Lambda + API Gateway + DynamoDB dedup
# -----------------------------------------------------------------------------

# --- DynamoDB dedup table ---

resource "aws_dynamodb_table" "dedup" {
  name         = "${var.name_prefix}-whatsapp-dedup"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "message_id"

  attribute {
    name = "message_id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  server_side_encryption {
    enabled = true
  }

  point_in_time_recovery {
    enabled = var.environment != "dev"
  }

  tags = { Name = "${var.name_prefix}-whatsapp-dedup" }
}

# --- Secrets Manager ---

resource "aws_secretsmanager_secret" "whatsapp" {
  name                    = "${var.name_prefix}-whatsapp-secrets"
  description             = "WhatsApp API credentials for ${var.name_prefix}"
  recovery_window_in_days = var.environment == "prod" ? 30 : 0
  tags                    = { Name = "${var.name_prefix}-whatsapp-secrets" }
}

resource "aws_secretsmanager_secret_version" "whatsapp" {
  secret_id = aws_secretsmanager_secret.whatsapp.id
  secret_string = jsonencode({
    WHATSAPP_ACCESS_TOKEN = var.whatsapp_token
    WHATSAPP_APP_SECRET   = var.whatsapp_app_secret
    WHATSAPP_VERIFY_TOKEN = var.whatsapp_verify_token
  })
}

# --- Lambda function ---

resource "null_resource" "lambda_build" {
  triggers = {
    source_hash = sha256(join("", [for f in fileset(var.lambda_source_dir, "*.py") : filemd5("${var.lambda_source_dir}/${f}")]))
  }

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command = <<-EOT
      set -euo pipefail
      LAMBDA_ZIP="${abspath(path.module)}/lambda.zip"
      SRC_DIR="${abspath(var.lambda_source_dir)}"
      BUILD_DIR=$(mktemp -d)
      cp "$SRC_DIR"/*.py "$BUILD_DIR/"
      pip install pydantic -t "$BUILD_DIR" --quiet --platform manylinux2014_aarch64 --only-binary=:all: --python-version 3.12
      cd "$BUILD_DIR" && zip -r "$LAMBDA_ZIP" . -x '__pycache__/*' '*.dist-info/*' > /dev/null
      rm -rf "$BUILD_DIR"
    EOT
  }
}

resource "aws_lambda_function" "whatsapp" {
  function_name                  = "${var.name_prefix}-whatsapp"
  role                           = var.lambda_role_arn
  handler                        = "lambda_handler.lambda_handler"
  runtime                        = "python3.12"
  architectures                  = ["arm64"]
  timeout                        = 120
  memory_size                    = 256
  reserved_concurrent_executions = 10
  filename                       = "${path.module}/lambda.zip"
  source_code_hash               = filebase64sha256("${path.module}/lambda.zip")

  depends_on = [null_resource.lambda_build]

  tracing_config {
    mode = "Active"
  }

  environment {
    variables = {
      WHATSAPP_SECRET_ARN      = aws_secretsmanager_secret.whatsapp.arn
      WHATSAPP_PHONE_NUMBER_ID = var.whatsapp_phone_number_id
      AGENTCORE_AGENT_NAME     = var.agentcore_runtime_arn
      AGENTCORE_MEMORY_ID      = var.agentcore_memory_id
      DOMAIN_SLUG              = var.domain_slug
      DEDUP_TABLE_NAME         = aws_dynamodb_table.dedup.name
      ERROR_MESSAGE_GENERIC    = var.error_message_generic
    }
  }

  dynamic "vpc_config" {
    for_each = length(var.private_subnet_ids) > 0 ? [1] : []
    content {
      subnet_ids         = var.private_subnet_ids
      security_group_ids = [var.lambda_security_group_id]
    }
  }

  tags = { Name = "${var.name_prefix}-whatsapp" }
}

# --- API Gateway ---

resource "aws_apigatewayv2_api" "whatsapp" {
  name          = "${var.name_prefix}-whatsapp-api"
  protocol_type = "HTTP"

  tags = { Name = "${var.name_prefix}-whatsapp-api" }
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.whatsapp.id
  name        = var.environment
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit = 100
    throttling_rate_limit  = 50
  }

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      method         = "$context.httpMethod"
      path           = "$context.path"
      status         = "$context.status"
      latency        = "$context.responseLatency"
    })
  }
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/apigateway/${var.name_prefix}-whatsapp"
  retention_in_days = 30
  kms_key_id        = var.log_kms_key_arn
  tags              = { Name = "${var.name_prefix}-whatsapp-api-logs" }
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.whatsapp.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.whatsapp.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "webhook_get" {
  api_id    = aws_apigatewayv2_api.whatsapp.id
  route_key = "GET /webhook"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "webhook_post" {
  api_id    = aws_apigatewayv2_api.whatsapp.id
  route_key = "POST /webhook"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.whatsapp.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.whatsapp.execution_arn}/*/*"
}

# --- WAF association ---

resource "aws_wafv2_web_acl_association" "api" {
  count        = var.waf_acl_arn != "" ? 1 : 0
  resource_arn = aws_apigatewayv2_stage.default.arn
  web_acl_arn  = var.waf_acl_arn
}
