terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.41"
    }
    opensearch = {
      source  = "opensearch-project/opensearch"
      version = ">= 2.2.0"
    }
    time = {
      source  = "hashicorp/time"
      version = ">= 0.9"
    }
    null = {
      source  = "hashicorp/null"
      version = ">= 3.2"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.domain_slug
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# OpenSearch provider — required by KB module for vector index creation.
# Only active when using OPENSEARCH_SERVERLESS vector store.
provider "opensearch" {
  url         = var.knowledge_base_enabled && var.vector_store_type == "OPENSEARCH_SERVERLESS" ? module.knowledge_base[0].opensearch_collection_endpoint : "https://localhost"
  healthcheck = false
}
