output "api_endpoint" {
  description = "The URL of the Frontend Gateway HTTP API"
  value       = aws_apigatewayv2_api.this.api_endpoint
}

output "lambda_function_arn" {
  description = "The ARN of the Frontend Gateway Lambda function"
  value       = module.lambda_function.lambda_function_arn
}
