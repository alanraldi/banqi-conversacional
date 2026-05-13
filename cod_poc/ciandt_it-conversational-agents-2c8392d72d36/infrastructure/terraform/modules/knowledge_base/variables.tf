variable "name_prefix" {
  type = string
}

variable "environment" {
  type = string
}

variable "aws_region" {
  type = string
}

variable "vector_store_type" {
  description = "Vector store type: S3 (cheap, serverless) or OPENSEARCH_SERVERLESS (hybrid search, low latency)"
  type        = string
  default     = "S3"
  validation {
    condition     = contains(["S3", "OPENSEARCH_SERVERLESS"], var.vector_store_type)
    error_message = "Must be S3 or OPENSEARCH_SERVERLESS."
  }
}

variable "embedding_model_id" {
  description = "Bedrock embedding model ID"
  type        = string
  default     = "amazon.titan-embed-text-v2:0"
}

variable "vector_dimension" {
  description = "Dimension of vectors produced by the embedding model"
  type        = number
  default     = 1024
}

variable "chunking_strategy" {
  description = "Chunking strategy: DEFAULT, FIXED_SIZE, SEMANTIC, HIERARCHICAL, NONE"
  type        = string
  default     = "FIXED_SIZE"
  validation {
    condition     = contains(["DEFAULT", "FIXED_SIZE", "SEMANTIC", "HIERARCHICAL", "NONE"], var.chunking_strategy)
    error_message = "Must be DEFAULT, FIXED_SIZE, SEMANTIC, HIERARCHICAL, or NONE."
  }
}

variable "fixed_size_max_tokens" {
  description = "Max tokens per chunk (FIXED_SIZE strategy)"
  type        = number
  default     = 300
}

variable "fixed_size_overlap_percentage" {
  description = "Overlap percentage between chunks (FIXED_SIZE strategy)"
  type        = number
  default     = 20
}

variable "semantic_max_tokens" {
  description = "Max tokens per chunk (SEMANTIC strategy)"
  type        = number
  default     = 500
}

variable "semantic_buffer_size" {
  description = "Buffer size (SEMANTIC strategy)"
  type        = number
  default     = 1
}

variable "semantic_breakpoint_percentile_threshold" {
  description = "Breakpoint percentile threshold (SEMANTIC strategy)"
  type        = number
  default     = 95
}

variable "kb_docs_path" {
  description = "Local path to KB documents directory"
  type        = string
}

variable "aoss_vpce_id" {
  description = "VPC Endpoint ID for OpenSearch Serverless (empty when not using AOSS)"
  type        = string
  default     = ""
}
