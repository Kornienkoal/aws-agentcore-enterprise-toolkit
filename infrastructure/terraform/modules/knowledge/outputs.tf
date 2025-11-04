# Knowledge Module Outputs
# Exports Knowledge Base identifiers and OpenSearch collection endpoint

output "knowledge_base_id" {
  description = "ID of the Bedrock Knowledge Base"
  value       = var.enable_knowledge_base ? aws_bedrockagent_knowledge_base.this[0].id : null
}

output "knowledge_base_arn" {
  description = "ARN of the Bedrock Knowledge Base"
  value       = var.enable_knowledge_base ? aws_bedrockagent_knowledge_base.this[0].arn : null
}

output "opensearch_endpoint" {
  description = "OpenSearch Serverless collection endpoint"
  value       = var.enable_knowledge_base ? aws_opensearchserverless_collection.vectors[0].collection_endpoint : null
}

output "data_source_bucket" {
  description = "S3 bucket for knowledge base data source"
  value       = var.enable_knowledge_base ? aws_s3_bucket.data_source[0].bucket : null
}

output "data_source_bucket_arn" {
  description = "ARN of data source S3 bucket"
  value       = var.enable_knowledge_base ? aws_s3_bucket.data_source[0].arn : null
}

# SSM Parameters
resource "aws_ssm_parameter" "kb_id" {
  count = var.enable_knowledge_base ? 1 : 0
  name  = "${module.shared.ssm_prefix}/kb/kb_id"
  type  = "String"
  value = aws_bedrockagent_knowledge_base.this[0].id
  tags  = module.shared.common_tags
}

resource "aws_ssm_parameter" "kb_arn" {
  count = var.enable_knowledge_base ? 1 : 0
  name  = "${module.shared.ssm_prefix}/kb/kb_arn"
  type  = "String"
  value = aws_bedrockagent_knowledge_base.this[0].arn
  tags  = module.shared.common_tags
}

resource "aws_ssm_parameter" "data_source_bucket" {
  count = var.enable_knowledge_base ? 1 : 0
  name  = "${module.shared.ssm_prefix}/kb/data_source_bucket"
  type  = "String"
  value = aws_s3_bucket.data_source[0].bucket
  tags  = module.shared.common_tags
}

resource "aws_ssm_parameter" "opensearch_endpoint" {
  count = var.enable_knowledge_base ? 1 : 0
  name  = "${module.shared.ssm_prefix}/kb/opensearch_endpoint"
  type  = "String"
  value = aws_opensearchserverless_collection.vectors[0].collection_endpoint
  tags  = module.shared.common_tags
}
