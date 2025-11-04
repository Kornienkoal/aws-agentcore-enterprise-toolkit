# Shared Locals - Tagging and Naming
#
# Provides common locals for resource naming and tagging across all modules.
# Reference: research.md D4 (Tagging & Naming Conventions)

locals {
  # Normalize agent namespace for resource naming (replace / with -)
  namespace_normalized = replace(var.agent_namespace, "/", "-")

  # Resource name prefix: {namespace}-{component}-{env}
  # Used for AWS resources that support hyphens (IAM roles, Lambda functions, etc.)
  name_prefix = "${local.namespace_normalized}-${var.component}-${var.environment}"

  # Bedrock AgentCore name prefix: {Namespace}{Component}{Env} in CamelCase
  # Used for Bedrock AgentCore resources (Gateway, Memory) which require alphanumeric + underscores
  # and work best with CamelCase naming (e.g., AgentcoreGatewayDev, AgentcoreMemoryDev)
  agentcore_name_prefix = "${title(replace(local.namespace_normalized, "-", ""))}${title(var.component)}${title(var.environment)}"

  # Common tags applied to all resources
  common_tags = merge(
    var.common_tags,
    {
      Environment    = var.environment
      AgentNamespace = var.agent_namespace
      Component      = var.component
    }
  )

  # SSM parameter path prefix: /agentcore/{env}/{component}
  ssm_prefix = "/agentcore/${var.environment}/${var.component}"
}

variable "agent_namespace" {
  description = "Agent namespace (e.g., myorg/team)"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod"
  }
}

variable "component" {
  description = "Component name (identity, gateway, runtime, memory, knowledge, observability)"
  type        = string
}

variable "common_tags" {
  description = "Common tags from globals/tagging.tfvars"
  type        = map(string)
  default     = {}
}
