#!/usr/bin/env bash
# AgentCore Infrastructure Validation Script
#
# Validates all infrastructure components are deployed and SSM parameters exist.
# Implements: T044 [US1], FR-015 (validation and troubleshooting)
#
# Usage:
#   ./scripts/infra/validate.sh <environment>
#
# Example:
#   ./scripts/infra/validate.sh dev

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT="${1:-dev}"
AWS_REGION="${AWS_REGION:-us-east-1}"
SSM_PREFIX="/agentcore/${ENVIRONMENT}"

# Counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# Validation functions
check_ssm_parameter() {
    local param_name="$1"
    local description="$2"

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    if aws ssm get-parameter \
        --name "${param_name}" \
        --region "${AWS_REGION}" \
        --query "Parameter.Value" \
        --output text &>/dev/null; then
        echo -e "${GREEN}✓${NC} ${description}"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        echo -e "${RED}✗${NC} ${description} (${param_name} not found)"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

check_cognito_pool() {
    local pool_id
    pool_id=$(aws ssm get-parameter \
        --name "${SSM_PREFIX}/identity/pool_id" \
        --region "${AWS_REGION}" \
        --query "Parameter.Value" \
        --output text 2>/dev/null || echo "")

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    if [[ -n "${pool_id}" ]] && aws cognito-idp describe-user-pool \
        --user-pool-id "${pool_id}" \
        --region "${AWS_REGION}" &>/dev/null; then
        echo -e "${GREEN}✓${NC} Cognito User Pool exists and is accessible"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        echo -e "${RED}✗${NC} Cognito User Pool not found or inaccessible"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

check_bedrock_gateway() {
    local gateway_id
    gateway_id=$(aws ssm get-parameter \
        --name "${SSM_PREFIX}/gateway/gateway_id" \
        --region "${AWS_REGION}" \
        --query "Parameter.Value" \
        --output text 2>/dev/null || echo "")

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    if [[ -n "${gateway_id}" ]] && aws bedrock-agent get-agent-gateway \
        --gateway-id "${gateway_id}" \
        --region "${AWS_REGION}" &>/dev/null; then
        echo -e "${GREEN}✓${NC} Bedrock Gateway exists and is accessible"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        echo -e "${RED}✗${NC} Bedrock Gateway not found or inaccessible"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

check_bedrock_memory() {
    local memory_id
    memory_id=$(aws ssm get-parameter \
        --name "${SSM_PREFIX}/memory/memory_id" \
        --region "${AWS_REGION}" \
        --query "Parameter.Value" \
        --output text 2>/dev/null || echo "")

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    if [[ -n "${memory_id}" ]] && aws bedrock-agent get-agent-memory \
        --memory-id "${memory_id}" \
        --region "${AWS_REGION}" &>/dev/null; then
        echo -e "${GREEN}✓${NC} Bedrock Memory service exists and is accessible"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        echo -e "${RED}✗${NC} Bedrock Memory service not found or inaccessible"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

check_memory_strategies() {
    local enabled_strategies
    enabled_strategies=$(aws ssm get-parameter \
        --name "${SSM_PREFIX}/memory/enabled_strategies" \
        --region "${AWS_REGION}" \
        --query "Parameter.Value" \
        --output text 2>/dev/null || echo "")

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    if [[ -n "${enabled_strategies}" ]]; then
        echo -e "${GREEN}✓${NC} Memory strategies enabled: ${enabled_strategies}"

        # Validate individual strategies
        if echo "${enabled_strategies}" | grep -q "SHORT_TERM"; then
            echo -e "  ${GREEN}→${NC} SHORT_TERM memory configured"
        fi
        if echo "${enabled_strategies}" | grep -q "LONG_TERM"; then
            echo -e "  ${GREEN}→${NC} LONG_TERM memory configured"
        fi
        if echo "${enabled_strategies}" | grep -q "SEMANTIC"; then
            echo -e "  ${GREEN}→${NC} SEMANTIC memory configured"
        fi

        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        echo -e "${RED}✗${NC} Memory strategies not configured"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

check_observability_metrics() {
    local metrics_namespace
    metrics_namespace=$(aws ssm get-parameter \
        --name "${SSM_PREFIX}/observability/metrics_namespace" \
        --region "${AWS_REGION}" \
        --query "Parameter.Value" \
        --output text 2>/dev/null || echo "")

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    if [[ -n "${metrics_namespace}" ]]; then
        echo -e "${GREEN}✓${NC} CloudWatch metrics namespace: ${metrics_namespace}"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        echo -e "${RED}✗${NC} CloudWatch metrics not configured"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

check_observability_alarms() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    local alarm_count=0

    # Check gateway latency alarm
    if check_ssm_parameter "${SSM_PREFIX}/observability/alarms/gateway_latency" "Gateway Latency Alarm" >/dev/null 2>&1; then
        alarm_count=$((alarm_count + 1))
    fi

    # Check gateway errors alarm
    if check_ssm_parameter "${SSM_PREFIX}/observability/alarms/gateway_errors" "Gateway Errors Alarm" >/dev/null 2>&1; then
        alarm_count=$((alarm_count + 1))
    fi

    # Check memory throttles alarm
    if check_ssm_parameter "${SSM_PREFIX}/observability/alarms/memory_throttles" "Memory Throttles Alarm" >/dev/null 2>&1; then
        alarm_count=$((alarm_count + 1))
    fi

    if [[ ${alarm_count} -ge 3 ]]; then
        echo -e "${GREEN}✓${NC} CloudWatch alarms configured (${alarm_count} alarms)"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        echo -e "${RED}✗${NC} CloudWatch alarms incomplete (${alarm_count}/3 configured)"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

check_cloudwatch_dashboard() {
    local dashboard_name
    dashboard_name=$(aws ssm get-parameter \
        --name "${SSM_PREFIX}/observability/dashboard_name" \
        --region "${AWS_REGION}" \
        --query "Parameter.Value" \
        --output text 2>/dev/null || echo "")

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    if [[ -n "${dashboard_name}" ]] && aws cloudwatch get-dashboard \
        --dashboard-name "${dashboard_name}" \
        --region "${AWS_REGION}" &>/dev/null; then
        echo -e "${GREEN}✓${NC} CloudWatch dashboard exists: ${dashboard_name}"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        echo -e "${RED}✗${NC} CloudWatch dashboard not found"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

check_iam_role() {
    local role_arn
    role_arn=$(aws ssm get-parameter \
        --name "${SSM_PREFIX}/runtime/execution_role_arn" \
        --region "${AWS_REGION}" \
        --query "Parameter.Value" \
        --output text 2>/dev/null || echo "")

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    if [[ -n "${role_arn}" ]]; then
        local role_name
        role_name=$(echo "${role_arn}" | awk -F'/' '{print $NF}')

        if aws iam get-role \
            --role-name "${role_name}" &>/dev/null; then
            echo -e "${GREEN}✓${NC} IAM execution role exists and is accessible"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
            return 0
        fi
    fi

    echo -e "${RED}✗${NC} IAM execution role not found or inaccessible"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
    return 1
}

check_cloudwatch_logs() {
    local log_group
    log_group=$(aws ssm get-parameter \
        --name "${SSM_PREFIX}/observability/invocations_log_group" \
        --region "${AWS_REGION}" \
        --query "Parameter.Value" \
        --output text 2>/dev/null || echo "")

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    if [[ -n "${log_group}" ]] && aws logs describe-log-groups \
        --log-group-name-prefix "${log_group}" \
        --region "${AWS_REGION}" \
        --query "logGroups[?logGroupName=='${log_group}']" \
        --output text | grep -q .; then
        echo -e "${GREEN}✓${NC} CloudWatch log groups exist"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        echo -e "${RED}✗${NC} CloudWatch log groups not found"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

# Main validation flow
main() {
    echo "========================================="
    echo "AgentCore Infrastructure Validation"
    echo "========================================="
    echo "Environment: ${ENVIRONMENT}"
    echo "Region: ${AWS_REGION}"
    echo "SSM Prefix: ${SSM_PREFIX}"
    echo ""

    # Check AWS credentials
    if ! aws sts get-caller-identity &>/dev/null; then
        echo -e "${RED}ERROR:${NC} AWS credentials not configured or invalid"
        exit 1
    fi

    echo "========================================="
    echo "1. Identity Module (Cognito)"
    echo "========================================="
    check_ssm_parameter "${SSM_PREFIX}/identity/pool_id" "Cognito User Pool ID"
    check_ssm_parameter "${SSM_PREFIX}/identity/machine_client_id" "M2M Client ID"
    check_ssm_parameter "${SSM_PREFIX}/identity/client_secret" "M2M Client Secret"
    check_ssm_parameter "${SSM_PREFIX}/identity/domain" "Cognito Domain"
    check_cognito_pool
    echo ""

    echo "========================================="
    echo "2. Gateway Module (Bedrock Gateway)"
    echo "========================================="
    check_ssm_parameter "${SSM_PREFIX}/gateway/gateway_id" "Bedrock Gateway ID"
    check_ssm_parameter "${SSM_PREFIX}/gateway/gateway_arn" "Bedrock Gateway ARN"
    check_ssm_parameter "${SSM_PREFIX}/gateway/invoke_url" "Gateway Invoke URL"
    check_ssm_parameter "${SSM_PREFIX}/gateway/role_arn" "Gateway IAM Role ARN"
    check_bedrock_gateway
    echo ""

    echo "========================================="
    echo "3. Runtime Module (IAM Execution)"
    echo "========================================="
    check_ssm_parameter "${SSM_PREFIX}/runtime/execution_role_arn" "Execution Role ARN"
    check_ssm_parameter "${SSM_PREFIX}/runtime/log_group_name" "Runtime Log Group"
    check_ssm_parameter "${SSM_PREFIX}/runtime/xray_enabled" "X-Ray Tracing Status"
    check_iam_role
    echo ""

    echo "========================================="
    echo "4. Memory Module (Bedrock Memory)"
    echo "========================================="
    check_ssm_parameter "${SSM_PREFIX}/memory/memory_id" "Bedrock Memory ID"
    check_ssm_parameter "${SSM_PREFIX}/memory/memory_arn" "Bedrock Memory ARN"
    check_ssm_parameter "${SSM_PREFIX}/memory/enabled_strategies" "Enabled Strategies"
    check_bedrock_memory
    check_memory_strategies
    echo ""

    echo "========================================="
    echo "5. Knowledge Module (Optional)"
    echo "========================================="
    if check_ssm_parameter "${SSM_PREFIX}/knowledge/kb_id" "Knowledge Base ID" 2>/dev/null; then
        check_ssm_parameter "${SSM_PREFIX}/knowledge/kb_arn" "Knowledge Base ARN"
        check_ssm_parameter "${SSM_PREFIX}/knowledge/data_source_bucket" "S3 Data Source Bucket"
        echo -e "${YELLOW}ℹ${NC} Knowledge Base is enabled"
    else
        echo -e "${YELLOW}ℹ${NC} Knowledge Base is disabled (optional component)"
        # Decrement failed counter since this is optional
        FAILED_CHECKS=$((FAILED_CHECKS - 1))
        TOTAL_CHECKS=$((TOTAL_CHECKS - 1))
    fi
    echo ""

    echo "========================================="
    echo "6. Observability Module (CloudWatch/X-Ray)"
    echo "========================================="
    check_ssm_parameter "${SSM_PREFIX}/observability/invocations_log_group" "Invocations Log Group"
    check_ssm_parameter "${SSM_PREFIX}/observability/tools_log_group" "Tools Log Group"
    check_ssm_parameter "${SSM_PREFIX}/observability/gateway_log_group" "Gateway Log Group"
    check_ssm_parameter "${SSM_PREFIX}/observability/xray_enabled" "X-Ray Status"
    check_ssm_parameter "${SSM_PREFIX}/observability/xray_sampling_rate" "X-Ray Sampling Rate"
    check_cloudwatch_logs
    check_observability_metrics
    check_observability_alarms
    check_cloudwatch_dashboard
    echo ""

    # Summary
    echo "========================================="
    echo "Validation Summary"
    echo "========================================="
    echo "Total Checks: ${TOTAL_CHECKS}"
    echo -e "${GREEN}Passed: ${PASSED_CHECKS}${NC}"

    if [[ ${FAILED_CHECKS} -gt 0 ]]; then
        echo -e "${RED}Failed: ${FAILED_CHECKS}${NC}"
        echo ""
        echo -e "${RED}❌ Validation FAILED${NC}"
        echo "Some infrastructure components are missing or inaccessible."
        echo "Please run: cd infrastructure/terraform/envs/${ENVIRONMENT} && terraform apply"
        exit 1
    else
        echo -e "${GREEN}Failed: 0${NC}"
        echo ""
        echo -e "${GREEN}✅ All validations PASSED${NC}"
        echo "Infrastructure is correctly provisioned and accessible."
        exit 0
    fi
}

# Run validation
main "$@"
