# Identity Module Outputs
#
# Publishes outputs to SSM Parameter Store per constitution paths:
# /agentcore/{env}/identity/*
# Note: shared module imported in main.tf

# Output: User Pool ID
output "pool_id" {
  description = "Cognito User Pool ID"
  value       = aws_cognito_user_pool.main.id
}

output "pool_arn" {
  description = "Cognito User Pool ARN"
  value       = aws_cognito_user_pool.main.arn
}

# Output: Machine Client ID
output "machine_client_id" {
  description = "M2M App Client ID"
  value       = aws_cognito_user_pool_client.machine.id
}

# Output: Frontend Client ID
output "frontend_client_id" {
  description = "Frontend App Client ID"
  value       = aws_cognito_user_pool_client.frontend.id
}

# Output: User Pool Domain
output "domain" {
  description = "Cognito User Pool Domain"
  value       = aws_cognito_user_pool_domain.main.domain
}

# SSM Parameter: Pool ID
resource "aws_ssm_parameter" "pool_id" {
  name        = "${module.shared.ssm_prefix}/pool_id"
  description = "Cognito User Pool ID for ${var.environment}"
  type        = "String"
  value       = aws_cognito_user_pool.main.id

  tags = merge(
    module.shared.common_tags,
    {
      Name = "${module.shared.ssm_prefix}/pool_id"
    }
  )
}

resource "aws_ssm_parameter" "pool_arn" {
  name        = "${module.shared.ssm_prefix}/pool_arn"
  description = "Cognito User Pool ARN for ${var.environment}"
  type        = "String"
  value       = aws_cognito_user_pool.main.arn

  tags = merge(
    module.shared.common_tags,
    {
      Name = "${module.shared.ssm_prefix}/pool_arn"
    }
  )
}

# SSM Parameter: Machine Client ID
resource "aws_ssm_parameter" "machine_client_id" {
  name        = "${module.shared.ssm_prefix}/machine_client_id"
  description = "M2M App Client ID for ${var.environment}"
  type        = "String"
  value       = aws_cognito_user_pool_client.machine.id

  tags = merge(
    module.shared.common_tags,
    {
      Name = "${module.shared.ssm_prefix}/machine_client_id"
    }
  )
}

# SSM Parameter: Generic Client ID (alias for machine_client_id)
resource "aws_ssm_parameter" "client_id" {
  name        = "${module.shared.ssm_prefix}/client_id"
  description = "Generic App Client ID alias (mirrors machine_client_id) for ${var.environment}"
  type        = "String"
  value       = aws_cognito_user_pool_client.machine.id

  tags = merge(
    module.shared.common_tags,
    {
      Name = "${module.shared.ssm_prefix}/client_id"
    }
  )
}

# SSM Parameter: Client Secret (SecureString)
resource "aws_ssm_parameter" "client_secret" {
  name        = "${module.shared.ssm_prefix}/client_secret"
  description = "M2M App Client Secret for ${var.environment} (SecureString)"
  type        = "SecureString"
  value       = aws_cognito_user_pool_client.machine.client_secret

  tags = merge(
    module.shared.common_tags,
    {
      Name = "${module.shared.ssm_prefix}/client_secret"
    }
  )
}

# SSM Parameter: Frontend Client ID
resource "aws_ssm_parameter" "frontend_client_id" {
  name        = "${module.shared.ssm_prefix}/frontend_client_id"
  description = "Frontend App Client ID for ${var.environment}"
  type        = "String"
  value       = aws_cognito_user_pool_client.frontend.id

  tags = merge(
    module.shared.common_tags,
    {
      Name = "${module.shared.ssm_prefix}/frontend_client_id"
    }
  )
}

# SSM Parameter: Frontend Client Secret (SecureString)
resource "aws_ssm_parameter" "frontend_client_secret" {
  name        = "${module.shared.ssm_prefix}/frontend_client_secret"
  description = "Frontend App Client Secret for ${var.environment} (SecureString)"
  type        = "SecureString"
  value       = aws_cognito_user_pool_client.frontend.client_secret

  tags = merge(
    module.shared.common_tags,
    {
      Name = "${module.shared.ssm_prefix}/frontend_client_secret"
    }
  )
}

# SSM Parameter: User Pool Domain
resource "aws_ssm_parameter" "domain" {
  name        = "${module.shared.ssm_prefix}/domain"
  description = "Cognito User Pool Domain for ${var.environment}"
  type        = "String"
  value       = aws_cognito_user_pool_domain.main.domain

  tags = merge(
    module.shared.common_tags,
    {
      Name = "${module.shared.ssm_prefix}/domain"
    }
  )
}

# SSM Parameter: Cognito Domain (alias for domain)
resource "aws_ssm_parameter" "cognito_domain" {
  name        = "${module.shared.ssm_prefix}/cognito_domain"
  description = "Cognito User Pool Domain alias (mirrors domain) for ${var.environment}"
  type        = "String"
  value       = aws_cognito_user_pool_domain.main.domain

  tags = merge(
    module.shared.common_tags,
    {
      Name = "${module.shared.ssm_prefix}/cognito_domain"
    }
  )
}

# SSM Parameter: Default OAuth2 Scope (optional)
resource "aws_ssm_parameter" "scope" {
  name        = "${module.shared.ssm_prefix}/scope"
  description = "Default OAuth2 scope for ${var.environment} (optional)"
  type        = "String"
  value       = var.identity_scope

  tags = merge(
    module.shared.common_tags,
    {
      Name = "${module.shared.ssm_prefix}/scope"
    }
  )
}
