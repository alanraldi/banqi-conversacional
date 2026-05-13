# -----------------------------------------------------------------------------
# Network — VPC dual-mode (criar nova ou reutilizar existente)
# Recursos: VPC + 2 private subnets + 1 public subnet + NAT + IGW
#           5 Interface VPC Endpoints + 2 Gateway Endpoints
#           3 Security Groups (lambda / runtime / endpoints)
#           WAF WebACL com rate limit + managed rules
# -----------------------------------------------------------------------------

locals {
  # Quando vpc_mode = "existing", busca VPC pelo Name tag
  existing_vpc_id = var.vpc_mode == "existing" ? data.aws_vpc.existing[0].id : ""
  vpc_id          = var.vpc_mode == "create" ? aws_vpc.this[0].id : local.existing_vpc_id

  # Subnets a usar
  private_subnet_ids = var.vpc_mode == "create" ? [
    aws_subnet.private_a[0].id,
    aws_subnet.private_b[0].id,
  ] : data.aws_subnets.existing_private[0].ids
}

# =============================================================================
# DATA — VPC existente (apenas quando vpc_mode = "existing")
# =============================================================================

data "aws_vpc" "existing" {
  count = var.vpc_mode == "existing" ? 1 : 0
  filter {
    name   = "tag:Name"
    values = [var.vpc_name]
  }
}

data "aws_subnets" "existing_private" {
  count = var.vpc_mode == "existing" ? 1 : 0
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.existing[0].id]
  }
  filter {
    name   = "tag:Tier"
    values = ["private"]
  }
}

# =============================================================================
# VPC + Subnets (apenas quando vpc_mode = "create")
# =============================================================================

resource "aws_vpc" "this" {
  count                = var.vpc_mode == "create" ? 1 : 0
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = "${var.domain_slug}-${var.environment}-vpc" }
}

resource "aws_internet_gateway" "this" {
  count  = var.vpc_mode == "create" ? 1 : 0
  vpc_id = aws_vpc.this[0].id
  tags   = { Name = "${var.domain_slug}-${var.environment}-igw" }
}

resource "aws_subnet" "private_a" {
  count             = var.vpc_mode == "create" ? 1 : 0
  vpc_id            = aws_vpc.this[0].id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, 1)
  availability_zone = "${var.aws_region}a"
  tags              = { Name = "${var.domain_slug}-${var.environment}-private-a", Tier = "private" }
}

resource "aws_subnet" "private_b" {
  count             = var.vpc_mode == "create" ? 1 : 0
  vpc_id            = aws_vpc.this[0].id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, 2)
  availability_zone = "${var.aws_region}b"
  tags              = { Name = "${var.domain_slug}-${var.environment}-private-b", Tier = "private" }
}

resource "aws_subnet" "public" {
  count                   = var.vpc_mode == "create" ? 1 : 0
  vpc_id                  = aws_vpc.this[0].id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, 0)
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = true
  tags                    = { Name = "${var.domain_slug}-${var.environment}-public", Tier = "public" }
}

resource "aws_eip" "nat" {
  count  = var.vpc_mode == "create" ? 1 : 0
  domain = "vpc"
  tags   = { Name = "${var.domain_slug}-${var.environment}-nat-eip" }
}

resource "aws_nat_gateway" "this" {
  count         = var.vpc_mode == "create" ? 1 : 0
  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.public[0].id
  tags          = { Name = "${var.domain_slug}-${var.environment}-nat" }
}

resource "aws_route_table" "private" {
  count  = var.vpc_mode == "create" ? 1 : 0
  vpc_id = aws_vpc.this[0].id
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.this[0].id
  }
  tags = { Name = "${var.domain_slug}-${var.environment}-rt-private" }
}

resource "aws_route_table_association" "private_a" {
  count          = var.vpc_mode == "create" ? 1 : 0
  subnet_id      = aws_subnet.private_a[0].id
  route_table_id = aws_route_table.private[0].id
}

resource "aws_route_table_association" "private_b" {
  count          = var.vpc_mode == "create" ? 1 : 0
  subnet_id      = aws_subnet.private_b[0].id
  route_table_id = aws_route_table.private[0].id
}

# =============================================================================
# Security Groups
# =============================================================================

resource "aws_security_group" "lambda" {
  name        = "${var.domain_slug}-${var.environment}-sg-lambda"
  description = "Lambda WhatsApp handler — saída HTTPS para VPC Endpoints"
  vpc_id      = local.vpc_id

  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS para VPC Endpoints e internet"
  }

  tags = { Name = "${var.domain_slug}-${var.environment}-sg-lambda" }
}

resource "aws_security_group" "runtime" {
  name        = "${var.domain_slug}-${var.environment}-sg-runtime"
  description = "AgentCore Runtime — saída HTTPS para Bedrock, Secrets Manager e banQi API"
  vpc_id      = local.vpc_id

  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS para Bedrock, Secrets Manager, banQi API"
  }

  tags = { Name = "${var.domain_slug}-${var.environment}-sg-runtime" }
}

resource "aws_security_group" "endpoints" {
  name        = "${var.domain_slug}-${var.environment}-sg-endpoints"
  description = "VPC Endpoints — entrada HTTPS dos SGs lambda e runtime"
  vpc_id      = local.vpc_id

  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id, aws_security_group.runtime.id]
    description     = "HTTPS dos SGs lambda e runtime"
  }

  tags = { Name = "${var.domain_slug}-${var.environment}-sg-endpoints" }
}

# =============================================================================
# VPC Endpoints — Interface (5) + Gateway (2)
# =============================================================================

locals {
  interface_endpoints = {
    bedrock_runtime       = "com.amazonaws.${var.aws_region}.bedrock-runtime"
    bedrock_agent_runtime = "com.amazonaws.${var.aws_region}.bedrock-agent-runtime"
    secretsmanager        = "com.amazonaws.${var.aws_region}.secretsmanager"
    logs                  = "com.amazonaws.${var.aws_region}.logs"
    ssm                   = "com.amazonaws.${var.aws_region}.ssm"
  }
}

resource "aws_vpc_endpoint" "interface" {
  for_each = var.vpc_mode == "create" ? local.interface_endpoints : {}

  vpc_id              = local.vpc_id
  service_name        = each.value
  vpc_endpoint_type   = "Interface"
  subnet_ids          = local.private_subnet_ids
  security_group_ids  = [aws_security_group.endpoints.id]
  private_dns_enabled = true

  tags = { Name = "${var.domain_slug}-${var.environment}-vpce-${each.key}" }
}

resource "aws_vpc_endpoint" "dynamodb" {
  count             = var.vpc_mode == "create" ? 1 : 0
  vpc_id            = local.vpc_id
  service_name      = "com.amazonaws.${var.aws_region}.dynamodb"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private[0].id]
  tags              = { Name = "${var.domain_slug}-${var.environment}-vpce-dynamodb" }
}

resource "aws_vpc_endpoint" "s3" {
  count             = var.vpc_mode == "create" ? 1 : 0
  vpc_id            = local.vpc_id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private[0].id]
  tags              = { Name = "${var.domain_slug}-${var.environment}-vpce-s3" }
}

# =============================================================================
# WAF WebACL — rate limit + managed rules
# =============================================================================

resource "aws_wafv2_web_acl" "this" {
  name  = "${var.domain_slug}-${var.environment}-waf"
  scope = "REGIONAL"

  default_action {
    allow {}
  }

  rule {
    name     = "RateLimit"
    priority = 1

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = 1000
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "RateLimit"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWSCommonRules"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSCommonRules"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWSKnownBadInputs"
    priority = 3

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSKnownBadInputs"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.domain_slug}-${var.environment}-waf"
    sampled_requests_enabled   = true
  }

  tags = { Name = "${var.domain_slug}-${var.environment}-waf" }
}

# =============================================================================
# Outputs
# =============================================================================

output "private_subnet_ids" {
  value = local.private_subnet_ids
}

output "security_group_ids" {
  value = {
    lambda   = aws_security_group.lambda.id
    runtime  = aws_security_group.runtime.id
    endpoints = aws_security_group.endpoints.id
  }
}

output "waf_acl_arn" {
  value = aws_wafv2_web_acl.this.arn
}

output "vpc_id" {
  value = local.vpc_id
}

# =============================================================================
# Variables
# =============================================================================

variable "vpc_mode"    { type = string }
variable "vpc_name"    { type = string; default = "" }
variable "domain_slug" { type = string }
variable "environment" { type = string }
variable "aws_region"  { type = string }
variable "vpc_cidr"    { type = string; default = "10.0.0.0/16" }
