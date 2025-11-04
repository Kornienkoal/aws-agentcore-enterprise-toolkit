# Runtime Module Outputs
#
# Publishes outputs to SSM Parameter Store per constitution paths:
# /agentcore/{env}/runtime/*
# Note: shared module imported in main.tf

# Outputs
output "execution_role_arn" {
  description = "IAM execution role ARN"
  value       = aws_iam_role.execution.arn
}

output "execution_role_name" {
  description = "IAM execution role name"
  value       = aws_iam_role.execution.name
}

output "log_group_name" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.runtime.name
}

output "log_group_arn" {
  description = "CloudWatch log group ARN"
  value       = aws_cloudwatch_log_group.runtime.arn
}

# SSM Parameters
resource "aws_ssm_parameter" "execution_role_arn" {
  name        = "${module.shared.ssm_prefix}/execution_role_arn"
  description = "IAM execution role ARN for ${var.environment}"
  type        = "String"
  value       = aws_iam_role.execution.arn

  tags = merge(
    module.shared.common_tags,
    {
      Name = "${module.shared.ssm_prefix}/execution_role_arn"
    }
  )
}

resource "aws_ssm_parameter" "log_group_name" {
  name        = "${module.shared.ssm_prefix}/log_group_name"
  description = "CloudWatch log group name for ${var.environment}"
  type        = "String"
  value       = aws_cloudwatch_log_group.runtime.name

  tags = merge(
    module.shared.common_tags,
    {
      Name = "${module.shared.ssm_prefix}/log_group_name"
    }
  )
}

resource "aws_ssm_parameter" "execution_role_name" {
  name        = "${module.shared.ssm_prefix}/execution_role_name"
  description = "IAM execution role name for ${var.environment}"
  type        = "String"
  value       = aws_iam_role.execution.name

  tags = merge(
    module.shared.common_tags,
    {
      Name = "${module.shared.ssm_prefix}/execution_role_name"
    }
  )
}

resource "aws_ssm_parameter" "xray_enabled" {
  name        = "${module.shared.ssm_prefix}/xray_enabled"
  description = "X-Ray tracing enabled status for ${var.environment}"
  type        = "String"
  value       = tostring(var.xray_tracing_enabled)

  tags = merge(
    module.shared.common_tags,
    {
      Name = "${module.shared.ssm_prefix}/xray_enabled"
    }
  )
}
