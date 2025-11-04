#!/usr/bin/env bash
# Terraform Validation and Formatting Script
#
# Validates Terraform configuration, formats code, and runs linting.
# Usage: ./scripts/infra/terraform-validate.sh [path]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TF_DIR="${1:-${REPO_ROOT}/infrastructure/terraform}"

echo "=== Terraform Validation and Formatting ==="
echo "Target directory: ${TF_DIR}"
echo

# Check if directory exists
if [[ ! -d "${TF_DIR}" ]]; then
    echo "Error: Directory ${TF_DIR} does not exist"
    exit 1
fi

cd "${TF_DIR}"

# Format check
echo ">>> Running terraform fmt..."
if terraform fmt -check -recursive -diff; then
    echo "✓ Formatting check passed"
else
    echo "✗ Formatting issues found. Run: terraform fmt -recursive"
    exit 1
fi
echo

# Validation
echo ">>> Running terraform validate..."
# Initialize if needed (lightweight check)
if [[ ! -d ".terraform" ]]; then
    echo ">>> Initializing (backend=false for validation)..."
    terraform init -backend=false -upgrade=false
fi

if terraform validate; then
    echo "✓ Validation passed"
else
    echo "✗ Validation failed"
    exit 1
fi
echo

# TFLint (optional - only if installed)
if command -v tflint &> /dev/null; then
    echo ">>> Running tflint..."
    if tflint --config="${REPO_ROOT}/.tflint.hcl" --recursive; then
        echo "✓ TFLint passed"
    else
        echo "✗ TFLint found issues"
        exit 1
    fi
else
    echo "⚠ TFLint not installed, skipping (optional)"
fi
echo

echo "=== All checks passed ==="
