output "frontend_gateway_url" {
  description = "The URL of the Frontend Gateway HTTP API"
  value       = module.frontend_gateway.api_endpoint
}

output "cognito_user_pool_id" {
  description = "The ID of the Cognito User Pool"
  value       = module.identity.pool_id
}

output "cognito_client_id" {
  description = "The ID of the Cognito User Pool Client"
  value       = module.identity.frontend_client_id
}
