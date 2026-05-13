# -----------------------------------------------------------------------------
# IAM — 3 roles: Runtime (AgentCore), Lambda (WhatsApp handler), Gateway (MCP)
# -----------------------------------------------------------------------------

# =============================================================================
# AgentCore Runtime Role
# Permissões: ECR pull + Bedrock InvokeModel/ApplyGuardrail + AgentCore Memory
#             + Secrets Manager + CloudWatch
# =============================================================================

resource "aws_iam_role" "runtime" {
  name = "${var.name_prefix}-runtime-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "bedrock-agentcore.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = { Name = "${var.name_prefix}-runtime-role" }
}

resource "aws_iam_role_policy" "runtime" {
  name = "${var.name_prefix}-runtime-policy"
  role = aws_iam_role.runtime.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ECRPull"
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
        ]
        Resource = "*"
      },
      {
        Sid    = "BedrockModels"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "bedrock:ApplyGuardrail",
        ]
        Resource = "*"
      },
      {
        Sid    = "AgentCoreMemory"
        Effect = "Allow"
        Action = [
          "bedrock-agentcore:CreateMemory",
          "bedrock-agentcore:GetMemory",
          "bedrock-agentcore:ListMemories",
          "bedrock-agentcore:UpdateMemory",
          "bedrock-agentcore:DeleteMemory",
          "bedrock-agentcore:CreateEvent",
          "bedrock-agentcore:GetEvent",
          "bedrock-agentcore:ListEvents",
          "bedrock-agentcore:DeleteEvent",
          "bedrock-agentcore:RetrieveMemoryRecords",
          "bedrock-agentcore:GetMemoryRecord",
          "bedrock-agentcore:ListMemoryRecords",
          "bedrock-agentcore:DeleteMemoryRecord",
          "bedrock-agentcore:ConsolidateMemory",
        ]
        Resource = "*"
      },
      {
        Sid    = "SecretsManager"
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret",
        ]
        Resource = "arn:aws:secretsmanager:${var.aws_region}:${var.aws_account_id}:secret:${var.domain_slug}/*"
      },
      {
        Sid    = "CloudWatch"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${var.aws_account_id}:log-group:/aws/bedrock-agentcore/*"
      },
    ]
  })
}

# =============================================================================
# Lambda Role (WhatsApp handler)
# Permissões: DynamoDB dedup/sessions + AgentCore InvokeRuntime/CreateEvent
#             + Secrets Manager + CloudWatch + X-Ray
# =============================================================================

resource "aws_iam_role" "lambda" {
  name = "${var.name_prefix}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = { Name = "${var.name_prefix}-lambda-role" }
}

resource "aws_iam_role_policy" "lambda" {
  name = "${var.name_prefix}-lambda-policy"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DynamoDB"
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:DeleteItem",
          "dynamodb:UpdateItem",
        ]
        Resource = [
          "arn:aws:dynamodb:${var.aws_region}:${var.aws_account_id}:table/${var.name_prefix}-dedup",
          "arn:aws:dynamodb:${var.aws_region}:${var.aws_account_id}:table/${var.name_prefix}-sessions",
        ]
      },
      {
        Sid    = "AgentCoreRuntime"
        Effect = "Allow"
        Action = [
          "bedrock-agentcore:InvokeAgentRuntime",
          "bedrock-agentcore:InvokeAgentRuntimeWithResponseStream",
          "bedrock-agentcore:CreateEvent",
        ]
        Resource = "arn:aws:bedrock-agentcore:${var.aws_region}:${var.aws_account_id}:agent-runtime/${var.agent_name}"
      },
      {
        Sid    = "SecretsManager"
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret",
        ]
        Resource = "arn:aws:secretsmanager:${var.aws_region}:${var.aws_account_id}:secret:${var.domain_slug}/*"
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${var.aws_account_id}:log-group:/aws/lambda/${var.name_prefix}-*"
      },
      {
        Sid    = "XRay"
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords",
        ]
        Resource = "*"
      },
      {
        Sid    = "VPCNetworking"
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface",
        ]
        Resource = "*"
      },
    ]
  })
}

# =============================================================================
# Gateway Role (AgentCore MCP Gateway)
# Permissões: CloudWatch apenas (gateway usa credenciais IAM para targets HTTP)
# =============================================================================

resource "aws_iam_role" "gateway" {
  name = "${var.name_prefix}-gateway-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "bedrock-agentcore.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = { Name = "${var.name_prefix}-gateway-role" }
}

resource "aws_iam_role_policy" "gateway" {
  name = "${var.name_prefix}-gateway-policy"
  role = aws_iam_role.gateway.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "CloudWatch"
      Effect = "Allow"
      Action = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
      ]
      Resource = "arn:aws:logs:${var.aws_region}:${var.aws_account_id}:log-group:/aws/bedrock-agentcore/*"
    }]
  })
}

# =============================================================================
# Outputs
# =============================================================================

output "runtime_role_arn" { value = aws_iam_role.runtime.arn }
output "lambda_role_arn"  { value = aws_iam_role.lambda.arn }
output "gateway_role_arn" { value = aws_iam_role.gateway.arn }

# =============================================================================
# Variables
# =============================================================================

variable "name_prefix"    { type = string }
variable "domain_slug"    { type = string }
variable "agent_name"     { type = string }
variable "aws_account_id" { type = string }
variable "aws_region"     { type = string }
variable "environment"    { type = string }
variable "ecr_repo_name"  { type = string }
