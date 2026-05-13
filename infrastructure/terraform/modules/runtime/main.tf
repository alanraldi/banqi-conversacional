# -----------------------------------------------------------------------------
# ECR Repository
# -----------------------------------------------------------------------------

resource "aws_ecr_repository" "runtime" {
  name                 = var.ecr_repo_name
  image_tag_mutability = "IMMUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = { Name = var.ecr_repo_name }
}

resource "aws_ecr_lifecycle_policy" "runtime" {
  repository = aws_ecr_repository.runtime.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 10 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}

# -----------------------------------------------------------------------------
# Container build + push (local-exec)
# -----------------------------------------------------------------------------

resource "null_resource" "container_build" {
  triggers = {
    dockerfile_hash = filemd5("${var.project_root}/Dockerfile")
    source_hash     = sha256(join("", [for f in fileset("${var.project_root}/src", "**/*.py") : filemd5("${var.project_root}/src/${f}")]))
    pyproject_hash  = filemd5("${var.project_root}/pyproject.toml")
    image_tag       = var.image_tag
  }

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command     = <<-EOT
      set -euo pipefail

      aws ecr get-login-password --region ${var.aws_region} | \
        docker login --username AWS --password-stdin ${aws_ecr_repository.runtime.repository_url}

      docker build --platform linux/arm64 \
        -t ${aws_ecr_repository.runtime.repository_url}:${var.image_tag} \
        "${var.project_root}"

      docker push ${aws_ecr_repository.runtime.repository_url}:${var.image_tag}
    EOT
  }

  depends_on = [aws_ecr_repository.runtime]
}

# -----------------------------------------------------------------------------
# AgentCore Runtime
# -----------------------------------------------------------------------------

resource "aws_bedrockagentcore_agent_runtime" "this" {
  agent_runtime_name = replace(var.name_prefix, "-", "_")

  agent_runtime_artifact {
    container_configuration {
      container_uri = "${aws_ecr_repository.runtime.repository_url}:${var.image_tag}"
    }
  }

  role_arn              = var.role_arn
  environment_variables = var.environment_variables

  network_configuration {
    network_mode = var.network_mode

    dynamic "network_mode_config" {
      for_each = var.network_mode == "VPC" ? [1] : []
      content {
        subnets         = var.subnet_ids
        security_groups = var.security_group_ids
      }
    }
  }

  protocol_configuration {
    server_protocol = "HTTP"
  }

  description = "AgentCore Runtime para ${var.agent_name} — banQi Consignado"

  depends_on = [null_resource.container_build]
}

# -----------------------------------------------------------------------------
# AgentCore Runtime Endpoint
# -----------------------------------------------------------------------------

resource "aws_bedrockagentcore_agent_runtime_endpoint" "this" {
  agent_runtime_id = aws_bedrockagentcore_agent_runtime.this.agent_runtime_id
  name             = "${replace(var.name_prefix, "-", "_")}_endpoint"
  description      = "Runtime endpoint para ${var.agent_name}"
}
