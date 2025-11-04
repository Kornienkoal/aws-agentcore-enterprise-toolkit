# agentcore-common

> **Shared utilities library for Amazon Bedrock AgentCore agents**
> Authentication, configuration, observability, and common helpers

---

## 📦 Overview

`agentcore-common` provides reusable utilities that are shared across all agents in the workspace. This package follows the DRY (Don't Repeat Yourself) principle by centralizing common functionality.

**Key Capabilities**:
- 🔐 **Authentication** - Cognito M2M (Client Credentials flow), SSM parameter access
- ⚙️ **Configuration** - YAML config loading with SSM parameter resolution
- 📊 **Observability** - CloudWatch Logs, X-Ray tracing, custom metrics

---

## 🔖 Conventions

- SSM parameters follow the repo convention: `${SSM:/agentcore/{env}/...}`.
    - Examples: `/agentcore/dev/identity/pool_id`, `/agentcore/dev/gateway/gateway_id`, `/agentcore/dev/memory/memory_id`.
- For exact parameter names and environment setup, see `docs/README.md` → Infrastructure (Terraform).

## 🏗️ Module Structure

```
agentcore_common/
├── __init__.py           # Package exports
├── auth.py              # Authentication utilities
├── config.py            # Configuration loading
└── observability.py     # Observability helpers
```

---

## 📚 Modules

### `auth.py` - Authentication Utilities

**Purpose**: Cognito authentication and SSM parameter access

#### Functions

##### `get_ssm_parameter(name: str, with_decryption: bool = True) -> str`
Get parameter from AWS Systems Manager Parameter Store.

```python
from agentcore_common import get_ssm_parameter

# Get Cognito pool ID (env-scoped)
pool_id = get_ssm_parameter('/agentcore/dev/identity/pool_id')

# Get encrypted client secret
client_secret = get_ssm_parameter(
    '/agentcore/dev/identity/client_secret',
    with_decryption=True
)
```

**Parameters**:
- `name` (str): SSM parameter name (e.g., `/app/myagent/agentcore/pool_id`)
- `with_decryption` (bool): Decrypt SecureString parameters (default: `True`)

**Returns**: Parameter value as string

**Raises**: `ValueError` if parameter not found

---

##### `get_m2m_token(client_id: str, client_secret: str, token_url: str, scope: str) -> str`
Get M2M access token using OAuth2 Client Credentials flow.

```python
from agentcore_common import get_m2m_token, get_ssm_parameter

# Load credentials from SSM
client_id = get_ssm_parameter('/agentcore/dev/identity/machine_client_id')
client_secret = get_ssm_parameter('/agentcore/dev/identity/client_secret')
token_url = get_ssm_parameter('/agentcore/dev/identity/token_url')
scope = get_ssm_parameter('/agentcore/dev/identity/auth_scope')

# Get access token
access_token = get_m2m_token(client_id, client_secret, token_url, scope)
```

**Parameters**:
- `client_id` (str): Cognito App Client ID
- `client_secret` (str): App Client Secret
- `token_url` (str): Cognito OAuth2 token endpoint
- `scope` (str): OAuth2 scopes (space-separated)

**Returns**: Access token (JWT)

**Raises**: `requests.HTTPError` if token request fails

---

##### `get_auth_config(agent_namespace: str) -> dict`
Get complete authentication configuration from SSM (helper to read required identity parameters).

```python
from agentcore_common import get_auth_config

# Get auth parameters (paths follow the repo SSM convention)
auth_config = get_auth_config('customer-support')  # example identifier; see docs for exact paths

print(auth_config)
# {
#     'pool_id': 'us-east-1_abc123',
#     'machine_client_id': 'abc123...',
#     'client_secret': 'secret...',
#     'token_url': 'https://...',
#     'auth_scope': 'myagent-api/agent.invoke'
# }
```

**Parameters**:
- `agent_namespace` (str): Agent namespace (e.g., `app/myagent`)

**Returns**: Dictionary with authentication configuration

**Raises**: `RuntimeError` if infrastructure not deployed

---

### `config.py` - Configuration Loading

**Purpose**: Load and validate agent configuration from YAML with SSM parameter resolution

#### Functions

##### `load_agent_config(config_path: str, environment: str = 'dev') -> dict`
Load agent configuration from YAML file with environment overrides and SSM resolution.

```python
from agentcore_common import load_agent_config

# Load config with dev environment
config = load_agent_config('agent-config/customer-support.yaml', environment='dev')

print(config['agent']['model']['model_id'])
# 'anthropic.claude-3-haiku-20240307-v1:0' (cheaper dev model)

# Load config with prod environment
config = load_agent_config('agent-config/customer-support.yaml', environment='prod')

print(config['agent']['model']['model_id'])
# 'anthropic.claude-3-7-sonnet-20250219-v1:0' (production model)
```

**Parameters**:
- `config_path` (str): Path to YAML config file
- `environment` (str): Environment name (`dev`, `staging`, `prod`)

**Returns**: Configuration dictionary with resolved SSM parameters

**Features**:
- ✅ Environment-specific overrides
- ✅ SSM parameter resolution (`${SSM:/path/to/parameter}`)
- ✅ Pydantic validation (if schema provided)

---

##### `resolve_ssm_parameters(config: dict) -> dict`
Recursively resolve SSM parameter references in configuration.

```yaml
# agent-config/customer-support.yaml
agent:
  memory:
        memory_id: ${SSM:/agentcore/dev/memory/memory_id}
  authorization:
        client_id: ${SSM:/agentcore/dev/identity/machine_client_id}
```

```python
from agentcore_common import resolve_ssm_parameters

config = {
    'memory_id': '${SSM:/agentcore/dev/memory/memory_id}',
    'client_id': '${SSM:/agentcore/dev/identity/machine_client_id}'
}

resolved = resolve_ssm_parameters(config)
print(resolved)
# {
#     'memory_id': 'CustomerSupportMemory-abc123',
#     'client_id': 'abc123def456...'
# }
```

**Parameters**:
- `config` (dict): Configuration dictionary with SSM references

**Returns**: Configuration with resolved SSM parameter values

---

### `observability.py` - Observability Helpers

**Purpose**: CloudWatch Logs, X-Ray tracing, and custom metrics

#### Functions

##### `setup_logging(log_group: str, log_stream: str, level: str = 'INFO')`
Configure CloudWatch Logs for agent.

```python
from agentcore_common import setup_logging

setup_logging(
    log_group='/aws/agents/customer-support',
    log_stream='runtime-2025-01-15',
    level='INFO'
)

import logging
logger = logging.getLogger(__name__)
logger.info('Agent started')  # Logs to CloudWatch
```

**Parameters**:
- `log_group` (str): CloudWatch Log Group name
- `log_stream` (str): Log Stream name
- `level` (str): Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`)

---

##### `trace_function(func)`
Decorator for AWS X-Ray tracing.

```python
from agentcore_common import trace_function

@trace_function
def expensive_operation(data):
    # Function execution will appear in X-Ray trace
    result = process_data(data)
    return result
```

**Creates X-Ray subsegment** with:
- Function name
- Execution time
- Exceptions (if any)

---

##### `publish_metric(namespace: str, metric_name: str, value: float, unit: str = 'Count', dimensions: dict = None)`
Publish custom metric to CloudWatch.

```python
from agentcore_common import publish_metric

# Publish agent invocation count
publish_metric(
    namespace='AgentCore/CustomerSupport',
    metric_name='InvocationCount',
    value=1,
    unit='Count',
    dimensions={'Environment': 'prod'}
)

# Publish latency
publish_metric(
    namespace='AgentCore/CustomerSupport',
    metric_name='InvocationLatency',
    value=1.234,
    unit='Seconds',
    dimensions={'Environment': 'prod', 'Tool': 'check_warranty'}
)
```

**Parameters**:
- `namespace` (str): CloudWatch metric namespace
- `metric_name` (str): Metric name
- `value` (float): Metric value
- `unit` (str): CloudWatch unit (Count, Seconds, Milliseconds, etc.)
- `dimensions` (dict): Metric dimensions

---

## 🔧 Installation

### As Workspace Dependency (Recommended)

```bash
# From agent directory
cd agents/customer-support
uv add agentcore-common --workspace
```

This automatically adds to `pyproject.toml`:
```toml
dependencies = [
    "agentcore-common",
]

[tool.uv.sources]
agentcore-common = { workspace = true }
```

### Direct Install (Development)

```bash
cd packages/agentcore-common
uv pip install -e .
```

---

## 📖 Usage Examples

### Complete Authentication Flow

```python
from agentcore_common import get_auth_config, get_m2m_token

# 1. Get auth configuration from SSM
auth_config = get_auth_config('app/myagent')

# 2. Get M2M access token
access_token = get_m2m_token(
    client_id=auth_config['machine_client_id'],
    client_secret=auth_config['client_secret'],
    token_url=auth_config['token_url'],
    scope=auth_config['auth_scope']
)

# 3. Use token for API calls
headers = {'Authorization': f'Bearer {access_token}'}
```

### Load Agent Configuration

```python
from agentcore_common import load_agent_config

# Load config for current environment
config = load_agent_config(
    'agent-config/customer-support.yaml',
    environment=os.getenv('ENVIRONMENT', 'dev')
)

# Access configuration
model_id = config['agent']['model']['model_id']
system_prompt = config['agent']['system_prompt']
tools = config['agent']['tools']
```

### Observability Setup

```python
from agentcore_common import setup_logging, trace_function, publish_metric
import logging

# Setup logging
setup_logging(
    log_group='/aws/agents/customer-support',
    log_stream=f'runtime-{session_id}',
    level='INFO'
)

logger = logging.getLogger(__name__)

@trace_function
def process_request(payload):
    logger.info(f'Processing request: {payload}')

    # Your logic here
    result = your_agent.run(payload)

    # Publish metrics
    publish_metric(
        namespace='AgentCore/CustomerSupport',
        metric_name='RequestProcessed',
        value=1,
        dimensions={'Status': 'Success'}
    )

    return result
```

---

## 🧪 Testing

```bash
# Run tests
cd packages/agentcore-common
uv run pytest tests/

# With coverage
uv run pytest tests/ --cov=agentcore_common --cov-report=term-missing
```

---

## 📝 Development

### Adding New Utilities

1. Add module to `src/agentcore_common/`
2. Export in `__init__.py`
3. Add tests to `tests/`
4. Update this README

### Updating Dependencies

```bash
cd packages/agentcore-common
uv add <package-name>
uv lock  # Update workspace lockfile
```

---

## 🔗 Related Packages

- **agentcore-tools**: Tool integration library (Gateway, Memory, Identity)

---

## 📄 License

See [LICENSE](../../LICENSE) in repository root.
