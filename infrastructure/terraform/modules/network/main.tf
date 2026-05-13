# -----------------------------------------------------------------------------
# Network Module — banQi Consignado
# Dual mode: create new VPC or use existing
# vpc_mode = "create"   → cria VPC, subnets, IGW, NAT, route tables
# vpc_mode = "existing" → usa VPC existente por nome tag
# Ambos os modos criam: Security Groups, VPC Endpoints, WAF
# -----------------------------------------------------------------------------

locals {
  name_prefix = "banqi-consignado-${var.environment}"
  create_vpc  = var.vpc_mode == "create"
  vpc_id      = local.create_vpc ? aws_vpc.this[0].id : data.aws_vpc.existing[0].id
  azs         = ["${var.aws_region}a", "${var.aws_region}b"]

  private_subnet_ids = local.create_vpc ? aws_subnet.private[*].id : data.aws_subnets.existing_private[0].ids
  private_rt_id      = local.create_vpc ? aws_route_table.private[0].id : data.aws_route_tables.existing_private[0].ids[0]

  interface_endpoints = [
    "bedrock-runtime",
    "bedrock-agent-runtime",
    "secretsmanager",
    "logs",
    "ssm",
  ]
}

# =============================================================================
# MODE: existing — Data Sources
# =============================================================================

data "aws_vpc" "existing" {
  count = local.create_vpc ? 0 : 1

  filter {
    name   = "tag:Name"
    values = [var.vpc_name]
  }
}

data "aws_subnets" "existing_private" {
  count = local.create_vpc ? 0 : 1

  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.existing[0].id]
  }
  filter {
    name   = "tag:Name"
    values = ["*priv*"]
  }
}

data "aws_route_tables" "existing_private" {
  count = local.create_vpc ? 0 : 1

  filter {
    name   = "tag:Name"
    values = ["*priv*"]
  }
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.existing[0].id]
  }
}

# =============================================================================
# MODE: create — VPC + Subnets + IGW + NAT
# =============================================================================

resource "aws_vpc" "this" {
  count                = local.create_vpc ? 1 : 0
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = "${local.name_prefix}-vpc" }
}

resource "aws_subnet" "private" {
  count             = local.create_vpc ? 2 : 0
  vpc_id            = aws_vpc.this[0].id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone = local.azs[count.index]

  tags = { Name = "${local.name_prefix}-private-${local.azs[count.index]}" }
}

resource "aws_subnet" "public" {
  count             = local.create_vpc ? 1 : 0
  vpc_id            = aws_vpc.this[0].id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, 100)
  availability_zone = local.azs[0]

  tags = { Name = "${local.name_prefix}-public" }
}

resource "aws_internet_gateway" "this" {
  count  = local.create_vpc ? 1 : 0
  vpc_id = aws_vpc.this[0].id
  tags   = { Name = "${local.name_prefix}-igw" }
}

resource "aws_route_table" "public" {
  count  = local.create_vpc ? 1 : 0
  vpc_id = aws_vpc.this[0].id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this[0].id
  }
  tags = { Name = "${local.name_prefix}-public-rt" }
}

resource "aws_route_table_association" "public" {
  count          = local.create_vpc ? 1 : 0
  subnet_id      = aws_subnet.public[0].id
  route_table_id = aws_route_table.public[0].id
}

resource "aws_eip" "nat" {
  count  = local.create_vpc ? 1 : 0
  domain = "vpc"
  tags   = { Name = "${local.name_prefix}-nat-eip" }
}

resource "aws_nat_gateway" "this" {
  count         = local.create_vpc ? 1 : 0
  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.public[0].id
  tags          = { Name = "${local.name_prefix}-nat" }
}

resource "aws_route_table" "private" {
  count  = local.create_vpc ? 1 : 0
  vpc_id = aws_vpc.this[0].id
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.this[0].id
  }
  tags = { Name = "${local.name_prefix}-private-rt" }
}

resource "aws_route_table_association" "private" {
  count          = local.create_vpc ? 2 : 0
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[0].id
}

# =============================================================================
# SHARED — Security Groups (ambos os modos)
# =============================================================================

resource "aws_security_group" "lambda" {
  name_prefix = "${local.name_prefix}-lambda-"
  description = "Lambda functions SG — banQi Consignado"
  vpc_id      = local.vpc_id

  lifecycle { create_before_destroy = true }
  tags = { Name = "${local.name_prefix}-lambda-sg" }
}

resource "aws_security_group" "runtime" {
  name_prefix = "${local.name_prefix}-runtime-"
  description = "AgentCore Runtime SG — banQi Consignado"
  vpc_id      = local.vpc_id

  lifecycle { create_before_destroy = true }
  tags = { Name = "${local.name_prefix}-runtime-sg" }
}

resource "aws_security_group" "endpoints" {
  name_prefix = "${local.name_prefix}-vpce-"
  description = "VPC Endpoints SG — banQi Consignado"
  vpc_id      = local.vpc_id

  lifecycle { create_before_destroy = true }
  tags = { Name = "${local.name_prefix}-vpce-sg" }
}

# --- SG Rules ---

resource "aws_vpc_security_group_egress_rule" "lambda_to_runtime" {
  security_group_id            = aws_security_group.lambda.id
  referenced_security_group_id = aws_security_group.runtime.id
  from_port                    = 8080
  to_port                      = 8080
  ip_protocol                  = "tcp"
  description                  = "Allow Lambda to AgentCore Runtime"
}

resource "aws_vpc_security_group_egress_rule" "lambda_to_endpoints" {
  security_group_id            = aws_security_group.lambda.id
  referenced_security_group_id = aws_security_group.endpoints.id
  from_port                    = 443
  to_port                      = 443
  ip_protocol                  = "tcp"
  description                  = "Allow HTTPS to VPC endpoints"
}

resource "aws_vpc_security_group_ingress_rule" "runtime_from_lambda" {
  security_group_id            = aws_security_group.runtime.id
  referenced_security_group_id = aws_security_group.lambda.id
  from_port                    = 8080
  to_port                      = 8080
  ip_protocol                  = "tcp"
  description                  = "Allow Lambda on port 8080"
}

resource "aws_vpc_security_group_egress_rule" "runtime_to_endpoints" {
  security_group_id            = aws_security_group.runtime.id
  referenced_security_group_id = aws_security_group.endpoints.id
  from_port                    = 443
  to_port                      = 443
  ip_protocol                  = "tcp"
  description                  = "Allow HTTPS to VPC endpoints"
}

resource "aws_vpc_security_group_egress_rule" "runtime_to_internet" {
  security_group_id = aws_security_group.runtime.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
  description       = "Allow HTTPS to internet via NAT (APIs banQi + Cognito)"
}

resource "aws_vpc_security_group_ingress_rule" "endpoints_from_runtime" {
  security_group_id            = aws_security_group.endpoints.id
  referenced_security_group_id = aws_security_group.runtime.id
  from_port                    = 443
  to_port                      = 443
  ip_protocol                  = "tcp"
  description                  = "Allow HTTPS from Runtime"
}

resource "aws_vpc_security_group_ingress_rule" "endpoints_from_lambda" {
  security_group_id            = aws_security_group.endpoints.id
  referenced_security_group_id = aws_security_group.lambda.id
  from_port                    = 443
  to_port                      = 443
  ip_protocol                  = "tcp"
  description                  = "Allow HTTPS from Lambda"
}

# =============================================================================
# SHARED — VPC Endpoints (ambos os modos)
# =============================================================================

resource "aws_vpc_endpoint" "interface" {
  for_each = toset(local.interface_endpoints)

  vpc_id              = local.vpc_id
  service_name        = "com.amazonaws.${var.aws_region}.${each.key}"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = local.private_subnet_ids
  security_group_ids  = [aws_security_group.endpoints.id]

  tags = { Name = "${local.name_prefix}-vpce-${each.key}" }
}

resource "aws_vpc_endpoint" "dynamodb" {
  vpc_id            = local.vpc_id
  service_name      = "com.amazonaws.${var.aws_region}.dynamodb"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [local.private_rt_id]

  tags = { Name = "${local.name_prefix}-vpce-dynamodb" }
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = local.vpc_id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [local.private_rt_id]

  tags = { Name = "${local.name_prefix}-vpce-s3" }
}

# =============================================================================
# SHARED — WAF WebACL
# =============================================================================

resource "aws_wafv2_web_acl" "this" {
  name  = "${local.name_prefix}-waf"
  scope = "REGIONAL"

  default_action {
    allow {}
  }

  rule {
    name     = "RateLimitPerIP"
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
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.name_prefix}-rate-limit"
    }
  }

  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesCommonRuleSet"
      }
    }

    visibility_config {
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.name_prefix}-common-rules"
    }
  }

  rule {
    name     = "AWSManagedRulesKnownBadInputsRuleSet"
    priority = 3

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
      }
    }

    visibility_config {
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.name_prefix}-bad-inputs"
    }
  }

  visibility_config {
    sampled_requests_enabled   = true
    cloudwatch_metrics_enabled = true
    metric_name                = "${local.name_prefix}-waf"
  }

  tags = { Name = "${local.name_prefix}-waf" }
}
