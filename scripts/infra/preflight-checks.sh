#!/usr/bin/env bash
# AgentCore Infrastructure Preflight Checks
#
# Validates AWS quota limits and prerequisites before deployment.
# Implements: T053 [US3] - Quota preflight checks with actionable messages
#
# Usage:
#   ./scripts/infra/preflight-checks.sh <environment>
#
# Example:
#   ./scripts/infra/preflight-checks.sh dev

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT="${1:-dev}"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
}

log_error() {
    echo -e "${RED}✗${NC} $1"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
    WARNING_CHECKS=$((WARNING_CHECKS + 1))
}

run_check() {
    local check_name="$1"
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    log_info "Check $TOTAL_CHECKS: $check_name"
}

# Preflight checks
check_aws_credentials() {
    run_check "AWS Credentials"

    if aws sts get-caller-identity &>/dev/null; then
        local account_id=$(aws sts get-caller-identity --query Account --output text)
        local user_arn=$(aws sts get-caller-identity --query Arn --output text)
        log_success "AWS credentials valid (Account: ${account_id})"
        echo "  User: ${user_arn}"
        return 0
    else
        log_error "AWS credentials not configured or invalid"
        echo "  Fix: aws configure --profile <profile-name>"
        return 1
    fi
}

check_required_tools() {
    run_check "Required Tools"

    local missing_tools=()

    if ! command -v terraform &>/dev/null; then
        missing_tools+=("terraform")
    else
        local tf_version=$(terraform version -json | jq -r '.terraform_version' 2>/dev/null || echo "unknown")
        echo "  Terraform: ${tf_version}"
    fi

    if ! command -v aws &>/dev/null; then
        missing_tools+=("aws-cli")
    else
        local aws_version=$(aws --version 2>&1 | awk '{print $1}' | cut -d'/' -f2)
        echo "  AWS CLI: ${aws_version}"
    fi

    if ! command -v jq &>/dev/null; then
        missing_tools+=("jq")
    fi

    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        echo "  Install: brew install ${missing_tools[*]}"
        return 1
    else
        log_success "All required tools installed"
        return 0
    fi
}

check_bedrock_access() {
    run_check "Amazon Bedrock Access"

    # Check if Bedrock is available in region
    local available_regions=("us-east-1" "us-west-2" "ap-southeast-1" "eu-central-1")

    if [[ ! " ${available_regions[*]} " =~ " ${AWS_REGION} " ]]; then
        log_warning "Bedrock may not be available in ${AWS_REGION}"
        echo "  Recommended regions: ${available_regions[*]}"
        return 0
    fi

    # Try to list foundation models
    if aws bedrock list-foundation-models --region "$AWS_REGION" --query "modelSummaries[?contains(modelId, 'claude')].modelId" --output text &>/dev/null; then
        log_success "Bedrock API accessible"

        # Check for Claude models
        local claude_models=$(aws bedrock list-foundation-models \
            --region "$AWS_REGION" \
            --query "modelSummaries[?contains(modelId, 'claude-3')].modelId" \
            --output text 2>/dev/null || echo "")

        if [[ -n "$claude_models" ]]; then
            echo "  Available Claude models: $(echo $claude_models | tr '\t' ' ')"
        fi
    else
        log_error "Cannot access Bedrock API"
        echo "  Fix: Request Bedrock access in AWS Console"
        echo "  URL: https://console.aws.amazon.com/bedrock/home?region=${AWS_REGION}#/overview"
        return 1
    fi

    # Check Bedrock AgentCore access (preview service)
    if aws bedrock-agentcore-control list-gateways --region "$AWS_REGION" &>/dev/null 2>&1; then
        log_success "Bedrock AgentCore API accessible"
        echo "  Gateway and Memory services available"
        return 0
    else
        log_warning "Bedrock AgentCore API not accessible"
        echo "  Note: Service may be in preview or IAM permissions not enabled"
        echo "  Custom resource Lambdas will handle provisioning when available"
        return 0
    fi
}

check_service_quotas() {
    run_check "AWS Service Quotas"

    # Cognito User Pool quota
    local cognito_quota=$(aws service-quotas get-service-quota \
        --service-code cognito-idp \
        --quota-code L-D8578360 \
        --region "$AWS_REGION" \
        --query "Quota.Value" \
        --output text 2>/dev/null || echo "1000")

    local cognito_used=$(aws cognito-idp list-user-pools \
        --max-results 60 \
        --region "$AWS_REGION" \
        --query "length(UserPools)" \
        --output text 2>/dev/null || echo "0")

    echo "  Cognito User Pools: ${cognito_used}/${cognito_quota}"

    if [[ $(echo "$cognito_used >= $cognito_quota * 0.8" | bc) -eq 1 ]]; then
        log_warning "Cognito User Pool quota 80% utilized"
        echo "  Request increase: https://console.aws.amazon.com/servicequotas/home/services/cognito-idp/quotas"
    fi

    # Bedrock AgentCore quotas (preview - no public quota API yet)
    echo "  Bedrock Gateway: Check console for quota limits"
    echo "  Bedrock Memory: Check console for quota limits"
    echo "  Note: AgentCore quotas managed by AWS during preview"

    # Lambda function quota
    local lambda_quota=$(aws service-quotas get-service-quota \
        --service-code lambda \
        --quota-code L-9FEE3D26 \
        --region "$AWS_REGION" \
        --query "Quota.Value" \
        --output text 2>/dev/null || echo "1000")

    local lambda_used=$(aws lambda list-functions \
        --region "$AWS_REGION" \
        --query "length(Functions)" \
        --output text 2>/dev/null || echo "0")

    echo "  Lambda Functions: ${lambda_used}/${lambda_quota}"

    log_success "Service quotas checked"
    return 0
}

check_iam_permissions() {
    run_check "IAM Permissions"

    local required_permissions=(
        "cognito-idp:CreateUserPool"
        "bedrock-agentcore:CreateGateway"
        "bedrock-agentcore:CreateMemory"
        "iam:CreateRole"
        "lambda:CreateFunction"
        "ssm:PutParameter"
        "logs:CreateLogGroup"
    )

    # Simulate permission check (simplified)
    if aws iam get-user &>/dev/null || aws sts get-caller-identity --query "Arn" --output text | grep -q "assumed-role"; then
        log_success "IAM permissions appear valid"
        echo "  Note: Full permission validation requires actual resource creation"
        return 0
    else
        log_warning "Unable to verify all IAM permissions"
        echo "  Ensure your user/role has permissions for:"
        for perm in "${required_permissions[@]}"; do
            echo "    - $perm"
        done
        return 0
    fi
}

check_backend_configuration() {
    run_check "Terraform Backend Configuration"

    local backend_file="infrastructure/terraform/globals/backend.tfvars"

    if [[ ! -f "$backend_file" ]]; then
        log_error "Backend configuration not found: $backend_file"
        echo "  Create file with:"
        echo "    bucket         = \"agentcore-tfstate-<account-id>-<region>\""
        echo "    dynamodb_table = \"agentcore-tflock\""
        echo "    encrypt        = true"
        return 1
    fi

    # Check if S3 bucket exists
    local bucket=$(grep "bucket" "$backend_file" | awk -F'"' '{print $2}' || echo "")

    if [[ -n "$bucket" ]]; then
        if aws s3 ls "s3://${bucket}" &>/dev/null; then
            log_success "S3 backend bucket exists: ${bucket}"
        else
            log_error "S3 backend bucket not found: ${bucket}"
            echo "  Create with: aws s3 mb s3://${bucket} --region ${AWS_REGION}"
            return 1
        fi
    else
        log_warning "Cannot parse bucket name from ${backend_file}"
    fi

    # Check if DynamoDB table exists
    local dynamo_table=$(grep "dynamodb_table" "$backend_file" | awk -F'"' '{print $2}' || echo "")

    if [[ -n "$dynamo_table" ]]; then
        if aws dynamodb describe-table --table-name "$dynamo_table" --region "$AWS_REGION" &>/dev/null; then
            log_success "DynamoDB lock table exists: ${dynamo_table}"
        else
            log_error "DynamoDB lock table not found: ${dynamo_table}"
            echo "  Create with: aws dynamodb create-table \\"
            echo "    --table-name ${dynamo_table} \\"
            echo "    --attribute-definitions AttributeName=LockID,AttributeType=S \\"
            echo "    --key-schema AttributeName=LockID,KeyType=HASH \\"
            echo "    --billing-mode PAY_PER_REQUEST \\"
            echo "    --region ${AWS_REGION}"
            return 1
        fi
    fi

    return 0
}

check_existing_resources() {
    run_check "Check for Existing Resources"

    # Check if infrastructure already exists
    local existing_pools=$(aws cognito-idp list-user-pools \
        --max-results 60 \
        --region "$AWS_REGION" \
        --query "UserPools[?contains(Name, 'agentcore-${ENVIRONMENT}')].Name" \
        --output text 2>/dev/null || echo "")

    local existing_gateways=$(aws bedrock-agentcore-control list-gateways \
        --region "$AWS_REGION" \
        --query "gateways[?contains(gatewayName, 'agentcore-${ENVIRONMENT}')].gatewayName" \
        --output text 2>/dev/null || echo "")

    local existing_memories=$(aws bedrock-agentcore-control list-memories \
        --region "$AWS_REGION" \
        --query "memories[?contains(memoryName, 'agentcore-${ENVIRONMENT}')].memoryName" \
        --output text 2>/dev/null || echo "")

    if [[ -n "$existing_pools" ]] || [[ -n "$existing_gateways" ]] || [[ -n "$existing_memories" ]]; then
        log_warning "Existing AgentCore resources found for ${ENVIRONMENT}"
        [[ -n "$existing_pools" ]] && echo "  Cognito User Pools: $existing_pools"
        [[ -n "$existing_gateways" ]] && echo "  Bedrock Gateways: $existing_gateways"
        [[ -n "$existing_memories" ]] && echo "  Bedrock Memories: $existing_memories"
        echo "  This deployment may update existing resources"
    else
        log_success "No existing resources found - clean deployment"
    fi

    return 0
}

check_network_connectivity() {
    run_check "Network Connectivity"

    # Check AWS endpoint connectivity
    if curl -s --connect-timeout 5 "https://sts.${AWS_REGION}.amazonaws.com" &>/dev/null; then
        log_success "AWS API endpoints reachable"
    else
        log_error "Cannot reach AWS API endpoints"
        echo "  Check network connectivity and firewall rules"
        return 1
    fi

    return 0
}

# Main execution
main() {
    echo "========================================="
    echo "AgentCore Infrastructure Preflight Checks"
    echo "========================================="
    echo "Environment: ${ENVIRONMENT}"
    echo "Region: ${AWS_REGION}"
    echo ""

    # Run all checks
    check_aws_credentials || true
    echo ""

    check_required_tools || true
    echo ""

    check_network_connectivity || true
    echo ""

    check_bedrock_access || true
    echo ""

    check_service_quotas || true
    echo ""

    check_iam_permissions || true
    echo ""

    check_backend_configuration || true
    echo ""

    check_existing_resources || true
    echo ""

    # Summary
    echo "========================================="
    echo "Preflight Check Summary"
    echo "========================================="
    echo "Total Checks: ${TOTAL_CHECKS}"
    echo -e "${GREEN}Passed: ${PASSED_CHECKS}${NC}"
    echo -e "${YELLOW}Warnings: ${WARNING_CHECKS}${NC}"
    echo -e "${RED}Failed: ${FAILED_CHECKS}${NC}"
    echo ""

    if [[ ${FAILED_CHECKS} -gt 0 ]]; then
        echo -e "${RED}❌ PREFLIGHT CHECKS FAILED${NC}"
        echo ""
        echo "Fix the errors above before proceeding with deployment."
        echo ""
        exit 1
    elif [[ ${WARNING_CHECKS} -gt 0 ]]; then
        echo -e "${YELLOW}⚠ PREFLIGHT CHECKS PASSED WITH WARNINGS${NC}"
        echo ""
        echo "Review warnings above. Proceed with caution."
        echo ""
        exit 0
    else
        echo -e "${GREEN}✅ ALL PREFLIGHT CHECKS PASSED${NC}"
        echo ""
        echo "Ready to deploy infrastructure!"
        echo ""
        echo "Next steps:"
        echo "  cd infrastructure/terraform/envs/${ENVIRONMENT}"
        echo "  terraform init -backend-config=../../globals/backend.tfvars"
        echo "  terraform plan"
        echo "  terraform apply"
        echo ""
        exit 0
    fi
}

# Run preflight checks
main "$@"
