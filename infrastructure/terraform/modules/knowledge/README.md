# Knowledge Module

Provisions Amazon Bedrock Knowledge Base for RAG capabilities (optional).

## Features

- Bedrock Knowledge Base with vector embeddings
- S3 bucket for knowledge base data source
- OpenSearch Serverless collection for vector storage
- Configurable enable/disable flag
- SSM Parameter Store integration

**Note**: AWS S3 Vectors is preferred for cost-effective vector storage but is not yet supported in Terraform AWS provider v5.100.0 (S3 Vectors is in preview). Using OpenSearch Serverless as interim solution.

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| environment | Environment name | string | - | yes |
| agent_namespace | Agent namespace | string | - | yes |
| enable_knowledge_base | Enable KB provisioning | bool | false | no |
| embedding_model | Embedding model ID | string | amazon.titan-embed-text-v1 | no |
| tags | Additional tags | map(string) | {} | no |

## Outputs

| Name | Description |
|------|-------------|
| knowledge_base_id | Knowledge Base ID (if enabled) |
| knowledge_base_arn | Knowledge Base ARN (if enabled) |
| data_source_bucket | S3 bucket name for data source (if enabled) |
| opensearch_endpoint | OpenSearch Serverless endpoint (if enabled) |

## SSM Parameters

- `/{agent_namespace}/agentcore/{env}/kb/kb_id` (only if enabled)
- `/{agent_namespace}/agentcore/{env}/kb/kb_arn` (only if enabled)
- `/{agent_namespace}/agentcore/{env}/kb/data_source_bucket` (only if enabled)
- `/{agent_namespace}/agentcore/{env}/kb/opensearch_endpoint` (only if enabled)

## Notes

Set `enable_knowledge_base = false` to skip knowledge base provisioning (default).
