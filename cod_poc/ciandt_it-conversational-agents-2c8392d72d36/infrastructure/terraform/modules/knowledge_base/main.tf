# -----------------------------------------------------------------------------
# Bedrock Knowledge Base — S3 Vectors or OpenSearch Serverless
# vector_store_type = "S3"                    → Bedrock manages vector store
# vector_store_type = "OPENSEARCH_SERVERLESS" → We create AOSS collection
# -----------------------------------------------------------------------------

terraform {
  required_providers {
    opensearch = {
      source  = "opensearch-project/opensearch"
      version = ">= 2.2.0"
    }
  }
}

data "aws_caller_identity" "this" {}
data "aws_partition" "this" {}

locals {
  account_id        = data.aws_caller_identity.this.account_id
  partition         = data.aws_partition.this.partition
  oss_collection    = "${var.name_prefix}-kb-oss"
  kb_name           = "${var.name_prefix}-kb"
  embedding_model   = "arn:${local.partition}:bedrock:${var.aws_region}::foundation-model/${var.embedding_model_id}"
  vector_index_name = "bedrock-knowledge-base-default-index"
  use_oss           = var.vector_store_type == "OPENSEARCH_SERVERLESS"
}

# =============================================================================
# S3 Bucket — document storage (both modes)
# =============================================================================

resource "aws_s3_bucket" "kb_docs" {
  bucket        = "${var.name_prefix}-kb-docs"
  force_destroy = var.environment != "prod"
  tags          = { Name = "${var.name_prefix}-kb-docs" }
}

resource "aws_s3_bucket_versioning" "kb_docs" {
  bucket = aws_s3_bucket.kb_docs.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "kb_docs" {
  bucket = aws_s3_bucket.kb_docs.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "kb_docs" {
  bucket = aws_s3_bucket.kb_docs.id

  rule {
    id     = "transition-to-ia"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

resource "aws_s3_bucket_public_access_block" "kb_docs" {
  bucket                  = aws_s3_bucket.kb_docs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "kb_docs_ssl" {
  bucket = aws_s3_bucket.kb_docs.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "DenyInsecureTransport"
      Effect    = "Deny"
      Principal = "*"
      Action    = "s3:*"
      Resource  = [aws_s3_bucket.kb_docs.arn, "${aws_s3_bucket.kb_docs.arn}/*"]
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  })
  depends_on = [aws_s3_bucket_public_access_block.kb_docs]
}

# =============================================================================
# S3 Vectors — vector store (only for S3 vector_store_type)
# =============================================================================

resource "aws_s3vectors_vector_bucket" "kb" {
  count              = var.vector_store_type == "S3" ? 1 : 0
  vector_bucket_name = "${var.name_prefix}-kb-vectors"
  force_destroy      = var.environment != "prod"
  tags               = { Name = "${var.name_prefix}-kb-vectors" }
}

resource "aws_s3vectors_index" "kb" {
  count              = var.vector_store_type == "S3" ? 1 : 0
  vector_bucket_name = aws_s3vectors_vector_bucket.kb[0].vector_bucket_name
  index_name         = "${var.name_prefix}-kb-index"
  dimension          = var.vector_dimension
  distance_metric    = "cosine"
  data_type          = "float32"

  metadata_configuration {
    non_filterable_metadata_keys = ["AMAZON_BEDROCK_METADATA"]
  }
}

# =============================================================================
# OpenSearch Serverless — only when vector_store_type = OPENSEARCH_SERVERLESS
# =============================================================================

resource "aws_opensearchserverless_security_policy" "encryption" {
  count = local.use_oss ? 1 : 0
  name  = local.oss_collection
  type  = "encryption"
  policy = jsonencode({
    Rules       = [{ Resource = ["collection/${local.oss_collection}"], ResourceType = "collection" }]
    AWSOwnedKey = true
  })
}

resource "aws_opensearchserverless_security_policy" "network" {
  count = local.use_oss ? 1 : 0
  name  = local.oss_collection
  type  = "network"
  policy = var.aoss_vpce_id != "" ? jsonencode([{
    Rules           = [
      { ResourceType = "collection", Resource = ["collection/${local.oss_collection}"] },
      { ResourceType = "dashboard", Resource = ["collection/${local.oss_collection}"] },
    ]
    AllowFromPublic = false
    SourceVPCEs     = [var.aoss_vpce_id]
  }]) : jsonencode([{
    Rules           = [
      { ResourceType = "collection", Resource = ["collection/${local.oss_collection}"] },
      { ResourceType = "dashboard", Resource = ["collection/${local.oss_collection}"] },
    ]
    AllowFromPublic = true
  }])
}

resource "aws_opensearchserverless_access_policy" "data" {
  count = local.use_oss ? 1 : 0
  name  = local.oss_collection
  type  = "data"
  policy = jsonencode([{
    Rules = [
      {
        ResourceType = "index"
        Resource     = ["index/${local.oss_collection}/*"]
        Permission   = ["aoss:CreateIndex", "aoss:DeleteIndex", "aoss:DescribeIndex", "aoss:ReadDocument", "aoss:UpdateIndex", "aoss:WriteDocument"]
      },
      {
        ResourceType = "collection"
        Resource     = ["collection/${local.oss_collection}"]
        Permission   = ["aoss:CreateCollectionItems", "aoss:DescribeCollectionItems", "aoss:UpdateCollectionItems"]
      },
    ]
    Principal = [aws_iam_role.kb.arn, data.aws_caller_identity.this.arn]
  }])
}

resource "aws_opensearchserverless_collection" "kb" {
  count = local.use_oss ? 1 : 0
  name  = local.oss_collection
  type  = "VECTORSEARCH"

  depends_on = [
    aws_opensearchserverless_security_policy.encryption,
    aws_opensearchserverless_security_policy.network,
    aws_opensearchserverless_access_policy.data,
  ]
}

resource "opensearch_index" "kb" {
  count                          = local.use_oss ? 1 : 0
  name                           = local.vector_index_name
  number_of_shards               = "2"
  number_of_replicas             = "0"
  index_knn                      = true
  index_knn_algo_param_ef_search = "512"
  mappings = jsonencode({
    properties = {
      "bedrock-knowledge-base-default-vector" = {
        type      = "knn_vector"
        dimension = var.vector_dimension
        method    = { name = "hnsw", engine = "faiss", parameters = { m = 16, ef_construction = 512 }, space_type = "l2" }
      }
      "AMAZON_BEDROCK_METADATA"    = { type = "text", index = "false" }
      "AMAZON_BEDROCK_TEXT_CHUNK"  = { type = "text", index = "true" }
    }
  })
  force_destroy = true
  depends_on    = [aws_opensearchserverless_collection.kb]
}

# =============================================================================
# IAM Role — Bedrock KB execution role (both modes)
# =============================================================================

resource "aws_iam_role" "kb" {
  name = "AmazonBedrockExecutionRoleForKB_${local.kb_name}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "bedrock.amazonaws.com" }
      Condition = {
        StringEquals = { "aws:SourceAccount" = local.account_id }
        ArnLike      = { "aws:SourceArn" = "arn:${local.partition}:bedrock:${var.aws_region}:${local.account_id}:knowledge-base/*" }
      }
    }]
  })
}

resource "aws_iam_role_policy" "kb_model" {
  name = "BedrockInvokeModel"
  role = aws_iam_role.kb.name
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Action = "bedrock:InvokeModel", Effect = "Allow", Resource = local.embedding_model }]
  })
}

resource "aws_iam_role_policy" "kb_s3" {
  name = "S3ReadAccess"
  role = aws_iam_role.kb.name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Sid = "ListBucket", Action = "s3:ListBucket", Effect = "Allow", Resource = aws_s3_bucket.kb_docs.arn, Condition = { StringEquals = { "aws:ResourceAccount" = local.account_id } } },
      { Sid = "GetObject", Action = "s3:GetObject", Effect = "Allow", Resource = "${aws_s3_bucket.kb_docs.arn}/*", Condition = { StringEquals = { "aws:ResourceAccount" = local.account_id } } },
    ]
  })
}

resource "aws_iam_role_policy" "kb_s3_vectors" {
  count = var.vector_store_type == "S3" ? 1 : 0
  name  = "S3VectorsAccess"
  role  = aws_iam_role.kb.name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action   = ["s3vectors:QueryVectors", "s3vectors:GetVectors", "s3vectors:PutVectors", "s3vectors:DeleteVectors"]
        Effect   = "Allow"
        Resource = aws_s3vectors_index.kb[0].index_arn
      },
      {
        Action   = ["s3vectors:GetIndex", "s3vectors:ListIndexes"]
        Effect   = "Allow"
        Resource = aws_s3vectors_vector_bucket.kb[0].vector_bucket_arn
      },
    ]
  })
}

resource "aws_iam_role_policy" "kb_oss" {
  count = local.use_oss ? 1 : 0
  name  = "OpenSearchAccess"
  role  = aws_iam_role.kb.name
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Action = "aoss:APIAccessAll", Effect = "Allow", Resource = aws_opensearchserverless_collection.kb[0].arn }]
  })
}

resource "time_sleep" "iam_propagation" {
  create_duration = "20s"
  depends_on      = [aws_iam_role_policy.kb_s3, aws_iam_role_policy.kb_model]
}

# =============================================================================
# Bedrock Knowledge Base — conditional storage_configuration
# =============================================================================

resource "aws_bedrockagent_knowledge_base" "this" {
  name     = local.kb_name
  role_arn = aws_iam_role.kb.arn

  knowledge_base_configuration {
    type = "VECTOR"
    vector_knowledge_base_configuration {
      embedding_model_arn = local.embedding_model
    }
  }

  # S3 Vectors — managed vector store
  dynamic "storage_configuration" {
    for_each = var.vector_store_type == "S3" ? [1] : []
    content {
      type = "S3_VECTORS"
      s3_vectors_configuration {
        index_name        = aws_s3vectors_index.kb[0].index_name
        vector_bucket_arn = aws_s3vectors_vector_bucket.kb[0].vector_bucket_arn
      }
    }
  }

  # OpenSearch Serverless — we manage the collection
  dynamic "storage_configuration" {
    for_each = local.use_oss ? [1] : []
    content {
      type = "OPENSEARCH_SERVERLESS"
      opensearch_serverless_configuration {
        collection_arn    = aws_opensearchserverless_collection.kb[0].arn
        vector_index_name = local.vector_index_name
        field_mapping {
          vector_field   = "bedrock-knowledge-base-default-vector"
          text_field     = "AMAZON_BEDROCK_TEXT_CHUNK"
          metadata_field = "AMAZON_BEDROCK_METADATA"
        }
      }
    }
  }

  depends_on = [
    aws_iam_role_policy.kb_model,
    aws_iam_role_policy.kb_s3,
    opensearch_index.kb,
    aws_s3vectors_index.kb,
    time_sleep.iam_propagation,
  ]
}

# =============================================================================
# Data Source (S3) — both modes
# =============================================================================

resource "aws_bedrockagent_data_source" "s3" {
  knowledge_base_id = aws_bedrockagent_knowledge_base.this.id
  name              = "${local.kb_name}-datasource"

  data_source_configuration {
    type = "S3"
    s3_configuration {
      bucket_arn = aws_s3_bucket.kb_docs.arn
    }
  }

  dynamic "vector_ingestion_configuration" {
    for_each = var.chunking_strategy != "DEFAULT" ? [1] : []
    content {
      chunking_configuration {
        chunking_strategy = var.chunking_strategy

        dynamic "fixed_size_chunking_configuration" {
          for_each = var.chunking_strategy == "FIXED_SIZE" ? [1] : []
          content {
            max_tokens         = var.fixed_size_max_tokens
            overlap_percentage = var.fixed_size_overlap_percentage
          }
        }

        dynamic "semantic_chunking_configuration" {
          for_each = var.chunking_strategy == "SEMANTIC" ? [1] : []
          content {
            max_token                       = var.semantic_max_tokens
            buffer_size                     = var.semantic_buffer_size
            breakpoint_percentile_threshold = var.semantic_breakpoint_percentile_threshold
          }
        }
      }
    }
  }
}

# =============================================================================
# Upload KB documents + trigger ingestion (both modes)
# =============================================================================

resource "aws_s3_object" "kb_docs" {
  for_each = fileset(var.kb_docs_path, "**/*")

  bucket = aws_s3_bucket.kb_docs.id
  key    = each.value
  source = "${var.kb_docs_path}/${each.value}"
  etag   = filemd5("${var.kb_docs_path}/${each.value}")
}

resource "null_resource" "kb_sync" {
  triggers = {
    docs_hash = sha256(join("", [for f in fileset(var.kb_docs_path, "**/*") : filemd5("${var.kb_docs_path}/${f}")]))
  }

  provisioner "local-exec" {
    command = <<-EOT
      aws bedrock-agent start-ingestion-job \
        --knowledge-base-id ${aws_bedrockagent_knowledge_base.this.id} \
        --data-source-id ${aws_bedrockagent_data_source.s3.data_source_id} \
        --region ${var.aws_region}
    EOT
  }

  depends_on = [aws_s3_object.kb_docs, aws_bedrockagent_data_source.s3]
}
