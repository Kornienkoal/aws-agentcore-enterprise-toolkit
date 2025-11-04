# Knowledge Module Variables

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "agent_namespace" {
  description = "Agent namespace for resource naming"
  type        = string
}

variable "enable_knowledge_base" {
  description = "Enable knowledge base provisioning"
  type        = bool
  default     = false
}

variable "embedding_model_arn" {
  description = "ARN of embedding model for knowledge base"
  type        = string
  default     = "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1"
}

variable "embedding_model" {
  description = "Embedding model ID for knowledge base"
  type        = string
  default     = "amazon.titan-embed-text-v1"
}

variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default     = {}
}
