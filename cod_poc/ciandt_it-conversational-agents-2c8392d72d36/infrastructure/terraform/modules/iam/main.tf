# -----------------------------------------------------------------------------
# IAM — Runtime Role
# -----------------------------------------------------------------------------
data "aws_iam_policy_document" "runtime_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["bedrock-agentcore.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "runtime" {
  name               = "${var.name_prefix}-runtime-role"
  assume_role_policy = data.aws_iam_policy_document.runtime_assume.json
}

data "aws_iam_policy_document" "runtime_policy" {
  statement {
    sid    = "ECRPull"
    effect = "Allow"
    actions = [
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
      "ecr:BatchCheckLayerAvailability",
    ]
    resources = [
      "arn:aws:ecr:${var.aws_region}:${var.aws_account_id}:repository/${var.ecr_repo_name}"
    ]
  }

  statement {
    sid       = "ECRAuth"
    effect    = "Allow"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid    = "BedrockInvoke"
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
    ]
    resources = [
      # Foundation models (cross-region for inference profile routing)
      "arn:aws:bedrock:*::foundation-model/anthropic.claude-*",
      "arn:aws:bedrock:*::foundation-model/amazon.nova-*",
      # Inference profiles — us. prefix (cross-region failover)
      "arn:aws:bedrock:us-*:${var.aws_account_id}:inference-profile/us.anthropic.claude-*",
      "arn:aws:bedrock:us-*:${var.aws_account_id}:inference-profile/us.amazon.nova-*",
    ]
  }

  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = [
      "arn:aws:logs:${var.aws_region}:${var.aws_account_id}:log-group:/aws/bedrock-agentcore/*${replace(var.name_prefix, "-", "_")}*:*"
    ]
  }

  statement {
    sid    = "BedrockGuardrails"
    effect = "Allow"
    actions = [
      "bedrock:ApplyGuardrail",
    ]
    resources = [
      "arn:aws:bedrock:${var.aws_region}:${var.aws_account_id}:guardrail/*"
    ]
  }

  statement {
    sid    = "BedrockKBRetrieve"
    effect = "Allow"
    actions = [
      "bedrock:Retrieve",
      "bedrock:RetrieveAndGenerate",
    ]
    resources = [
      "arn:aws:bedrock:${var.aws_region}:${var.aws_account_id}:knowledge-base/*"
    ]
  }

  statement {
    sid    = "AgentCoreMemory"
    effect = "Allow"
    actions = [
      "bedrock-agentcore:RetrieveMemoryRecords",
      "bedrock-agentcore:ListMemoryRecords",
      "bedrock-agentcore:GetMemoryRecord",
      "bedrock-agentcore:DeleteMemoryRecord",
      "bedrock-agentcore:BatchCreateMemoryRecords",
      "bedrock-agentcore:BatchDeleteMemoryRecords",
      "bedrock-agentcore:BatchUpdateMemoryRecords",
      "bedrock-agentcore:StartMemoryExtractionJob",
      "bedrock-agentcore:ListMemoryExtractionJobs",
      "bedrock-agentcore:GetMemoryExtractionJob",
      "bedrock-agentcore:CreateEvent",
      "bedrock-agentcore:GetEvent",
      "bedrock-agentcore:ListEvents",
      "bedrock-agentcore:DeleteEvent",
    ]
    resources = [
      "arn:aws:bedrock-agentcore:${var.aws_region}:${var.aws_account_id}:memory/*"
    ]
  }
}

resource "aws_iam_role_policy" "runtime" {
  name   = "${var.name_prefix}-runtime-policy"
  role   = aws_iam_role.runtime.id
  policy = data.aws_iam_policy_document.runtime_policy.json
}

# -----------------------------------------------------------------------------
# IAM — Lambda Role (WhatsApp webhook)
# -----------------------------------------------------------------------------
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${var.name_prefix}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "lambda_policy" {
  statement {
    sid    = "DynamoDBDedup"
    effect = "Allow"
    actions = [
      "dynamodb:PutItem",
    ]
    resources = [
      "arn:aws:dynamodb:${var.aws_region}:${var.aws_account_id}:table/${var.name_prefix}-whatsapp-dedup"
    ]
  }

  statement {
    sid    = "AgentCoreInvoke"
    effect = "Allow"
    actions = [
      "bedrock-agentcore:InvokeAgentRuntime",
    ]
    resources = [
      "arn:aws:bedrock-agentcore:${var.aws_region}:${var.aws_account_id}:runtime/${replace(var.name_prefix, "-", "_")}*"
    ]
  }

  statement {
    sid    = "AgentCoreMemoryCreateEvent"
    effect = "Allow"
    actions = [
      "bedrock-agentcore:CreateEvent",
    ]
    resources = [
      "arn:aws:bedrock-agentcore:${var.aws_region}:${var.aws_account_id}:memory/*"
    ]
  }

  statement {
    sid    = "SecretsManagerRead"
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
    ]
    resources = [
      "arn:aws:secretsmanager:${var.aws_region}:${var.aws_account_id}:secret:${var.name_prefix}-whatsapp-secrets-*"
    ]
  }

  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = [
      "arn:aws:logs:${var.aws_region}:${var.aws_account_id}:log-group:/aws/lambda/${var.name_prefix}*:*"
    ]
  }

  statement {
    sid    = "XRayTracing"
    effect = "Allow"
    actions = [
      "xray:PutTraceSegments",
      "xray:PutTelemetryRecords",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "lambda" {
  name   = "${var.name_prefix}-lambda-policy"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.lambda_policy.json
}

# -----------------------------------------------------------------------------
# IAM — Gateway Role
# -----------------------------------------------------------------------------
data "aws_iam_policy_document" "gateway_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["bedrock-agentcore.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "gateway" {
  name               = "${var.name_prefix}-gateway-role"
  assume_role_policy = data.aws_iam_policy_document.gateway_assume.json
}

data "aws_iam_policy_document" "gateway_policy" {
  statement {
    sid    = "LambdaInvoke"
    effect = "Allow"
    actions = [
      "lambda:InvokeFunction",
    ]
    resources = concat(
      ["arn:aws:lambda:${var.aws_region}:${var.aws_account_id}:function:${var.name_prefix}-*"],
      var.gateway_tool_arns,
    )
  }

  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = [
      "arn:aws:logs:${var.aws_region}:${var.aws_account_id}:log-group:/aws/bedrock-agentcore/gateway/${var.name_prefix}*:*"
    ]
  }
}

resource "aws_iam_role_policy" "gateway" {
  name   = "${var.name_prefix}-gateway-policy"
  role   = aws_iam_role.gateway.id
  policy = data.aws_iam_policy_document.gateway_policy.json
}
