output "knowledge_base_id" {
  value = aws_bedrockagent_knowledge_base.this.id
}

output "knowledge_base_arn" {
  value = aws_bedrockagent_knowledge_base.this.arn
}

output "s3_bucket_name" {
  value = aws_s3_bucket.kb_docs.id
}

output "s3_bucket_arn" {
  value = aws_s3_bucket.kb_docs.arn
}

output "opensearch_collection_arn" {
  value = local.use_oss ? aws_opensearchserverless_collection.kb[0].arn : ""
}

output "opensearch_collection_endpoint" {
  value = local.use_oss ? aws_opensearchserverless_collection.kb[0].collection_endpoint : ""
}

output "data_source_id" {
  value = aws_bedrockagent_data_source.s3.data_source_id
}

output "vector_store_type" {
  value = var.vector_store_type
}
