# Lambda Custom Resources

This directory contains Lambda function source code for Terraform custom resource provisioners that manage Bedrock AgentCore services.

## Structure

```
custom-resources/
├── agentcore-gateway/
│   ├── lambda_function.py    # Gateway provisioner handler
│   └── requirements.txt      # Python dependencies
└── agentcore-memory/
    ├── lambda_function.py    # Memory provisioner handler
    └── requirements.txt      # Python dependencies
```

## Terraform Integration

Terraform automatically packages these Lambda functions during deployment:

- **Source:** `infrastructure/terraform/custom-resources/{function-name}/`
- **Build output:** `infrastructure/terraform/modules/{component}/.terraform/{function-name}_provisioner.zip`
- **Deployment:** Lambda function is created/updated with the packaged zip

The `archive_file` data source in each Terraform module handles packaging automatically. No manual build step required.

## Local Development & Testing

### Prerequisites

```bash
# Install Python dependencies
cd infrastructure/terraform/custom-resources/agentcore-gateway
pip install -r requirements.txt

cd ../agentcore-memory
pip install -r requirements.txt
```

### Testing Locally

**Run all infrastructure tests:**
```bash
cd infrastructure/terraform/custom-resources
python3 -m venv .venv
source .venv/bin/activate
pip install -r test-requirements.txt

# Run each module's tests separately (due to conftest.py naming)
pytest agentcore-gateway/tests/ -v
pytest agentcore-memory/tests/ -v
pytest agentcore-gateway-targets/tests/ -v
```

**Run specific module tests:**
```bash
pytest agentcore-gateway/tests/ -v      # Gateway only (10 tests)
pytest agentcore-memory/tests/ -v       # Memory only (11 tests)
pytest agentcore-gateway-targets/tests/ -v  # Targets only (4 tests)
```

**With coverage:**
```bash
pytest agentcore-gateway/tests/ --cov=agentcore-gateway --cov-report=term-missing
pytest agentcore-memory/tests/ --cov=agentcore-memory --cov-report=term-missing
pytest agentcore-gateway-targets/tests/ --cov=agentcore-gateway-targets --cov-report=term-missing
```

**Test structure:** Shared fixtures in `conftest.py` (aws_credentials, lambda_context, ssm_client). Module-specific fixtures in each `tests/conftest.py`. CI runs via `.github/workflows/test-custom-resources.yml`.

### Manual Packaging (Optional)

If you need to manually create a deployment package (for example, for testing outside Terraform):

```bash
#!/bin/bash
# Package a Lambda function manually

FUNCTION_NAME="agentcore-gateway"  # or "agentcore-memory"
SOURCE_DIR="infrastructure/terraform/custom-resources/${FUNCTION_NAME}"
OUTPUT_DIR="build"

# Create build directory
mkdir -p ${OUTPUT_DIR}

# Install dependencies into build directory
pip install -r ${SOURCE_DIR}/requirements.txt -t ${OUTPUT_DIR}/

# Copy source code
cp ${SOURCE_DIR}/lambda_function.py ${OUTPUT_DIR}/

# Create zip package
cd ${OUTPUT_DIR}
zip -r ../lambda-${FUNCTION_NAME}.zip .
cd ..

# Upload to Lambda (if needed for testing)
aws lambda update-function-code \
  --function-name ${FUNCTION_NAME}-dev-provisioner \
  --zip-file fileb://lambda-${FUNCTION_NAME}.zip
```

## Dependencies

All Lambda functions use:
- **boto3 >= 1.34.0** - AWS SDK (includes `bedrock-agentcore-control` client)
- **aws-lambda-powertools >= 2.31.0** - Observability and utilities
- **cfnresponse >= 1.1.2** - CloudFormation custom resource responses

## CI/CD

In CI pipelines, dependencies are NOT pre-installed into this directory. Terraform's `archive_file` handles packaging at deployment time by:

1. Reading `source_dir` (this directory)
2. Bundling Python dependencies listed in `requirements.txt`
3. Creating a deployment zip with all dependencies included
4. Uploading to Lambda

This keeps the repository clean—only source code is version-controlled, not vendor libraries.

## Important Notes

⚠️ **Do NOT commit vendor libraries** (boto3, botocore, etc.) to this directory. They are installed by Terraform's archive process.

✅ **Only commit:**
- `lambda_function.py` (source code)
- `requirements.txt` (dependency declarations)
- Tests (if any)
- Documentation

❌ **Never commit:**
- `boto3/`, `botocore/`, `aws_lambda_powertools/`, etc.
- `*.dist-info/` directories
- `__pycache__/`
- `lambda.zip` or any `.zip` files

The `.gitignore` at the repository root already excludes the old `lambda/` directory that contained pre-installed dependencies.

## Troubleshooting

### "Module not found" errors in IDE

This is expected—dependencies are installed at Terraform build time, not locally. To fix IDE errors:

```bash
# Install dependencies in a local virtual environment
cd infrastructure/terraform/custom-resources/agentcore-gateway
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Terraform packaging fails

Ensure `requirements.txt` is valid:

```bash
pip install -r requirements.txt --dry-run
```

### Lambda fails at runtime

Check CloudWatch Logs:

```bash
aws logs tail /aws/lambda/agentcore-gateway-dev-provisioner --follow
aws logs tail /aws/lambda/agentcore-memory-dev-provisioner --follow
```

## Architecture Alignment

This structure follows **Constitution I: AWS Native Services First** from `.github/copilot-instructions.md`:

- ✅ Infrastructure provisioned via Terraform (IaC)
- ✅ Custom resources only used where native Terraform support doesn't exist
- ✅ Lambda source kept minimal (dependencies installed at build time)
- ✅ Build artifacts excluded from version control

For more details, see:
- [Architecture Decisions](/.github/copilot-instructions.md)
- [Docs index](/docs/README.md)
