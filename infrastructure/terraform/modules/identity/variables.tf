# Identity Module Variables

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "agent_namespace" {
  description = "Agent namespace for resource naming (e.g., myorg/team)"
  type        = string
}

variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default     = {}
}

# Optional default OAuth2 scope to publish to SSM for clients that expect a single scope string
# Note: For Cognito client_credentials, resource-server scopes like "agentcore/invoke" may be used.
# This default satisfies consumers expecting an OIDC-style scope. Can be overridden per env.
variable "identity_scope" {
  description = "Default OAuth2 scope string to publish under /identity/scope (optional)"
  type        = string
  default     = "openid"
}
