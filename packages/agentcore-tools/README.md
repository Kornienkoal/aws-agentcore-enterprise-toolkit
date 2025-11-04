# agentcore-tools

> **Tool integration library for Amazon Bedrock AgentCore**
> Gateway client, Memory helpers, Identity decorators

---

## 📦 Overview

`agentcore-tools` provides client libraries and decorators for integrating with AgentCore services. This package simplifies interaction with Gateway (MCP tools), Memory (conversation context), and Identity (OAuth2 credentials).

**Key Capabilities**:
- 🛠️ **Gateway Client** - Invoke Lambda MCP tools via AgentCore Gateway
- 🧠 **Memory Helpers** - Store/retrieve conversation context

---

## 🔖 Conventions

- SSM parameters follow the repo convention: `${SSM:/agentcore/{env}/...}`.
    - Examples: `/agentcore/dev/gateway/gateway_id`, `/agentcore/dev/memory/memory_id`.
- For parameter names and setup, see `docs/README.md` → Infrastructure (Terraform).

## 🏗️ Module Structure

```
agentcore_tools/
├── __init__.py           # Package exports
├── gateway.py           # Gateway client for MCP tools
└── memory.py            # Memory helpers (Strands integration)
```

---

## 📚 Modules

### `gateway.py` - Gateway Client

**Purpose**: Invoke Lambda MCP tools deployed to AgentCore Gateway

#### Classes

##### `GatewayClient`
Client for invoking Gateway-deployed MCP tools.

```python
from agentcore_tools import GatewayClient

# Initialize client
gateway = GatewayClient(
    gateway_id='customersupport-gw-abc123',  # Or from SSM
    region='us-east-1'
)

# Invoke tool
result = gateway.invoke_tool(
    tool_name='check_warranty',
    input_data={
        'product_id': 'LAPTOP-2024',
        'serial_number': 'SN123456'
    }
)

print(result)
# {
#     'warranty_status': 'active',
#     'expiration_date': '2026-10-15',
#     'coverage': 'full'
# }
```

**Constructor Parameters**:
- `gateway_id` (str): AgentCore Gateway ID
- `region` (str): AWS region (default: `us-east-1`)
- `auth_token` (str, optional): Bearer token for authentication

**Methods**:

##### `invoke_tool(tool_name: str, input_data: dict) -> dict`
Invoke a Gateway tool (Lambda MCP function).

**Parameters**:
- `tool_name` (str): Tool name (e.g., `check_warranty`, `web_search`)
- `input_data` (dict): Tool input parameters

**Returns**: Tool output (dict)

**Raises**:
- `GatewayError`: If tool invocation fails
- `AuthenticationError`: If auth token is invalid

---

##### `list_tools() -> list[dict]`
List all available Gateway tools.

```python
tools = gateway.list_tools()

for tool in tools:
    print(f"{tool['name']}: {tool['description']}")

# Output:
# check_warranty: Verify product warranty status
# web_search: Search the internet for information
```

**Returns**: List of tool metadata (name, description, parameters)

---

#### Helper Function

##### `get_gateway_client(context: str) -> GatewayClient`
Create Gateway client using SSM configuration (e.g., loads `/agentcore/{env}/gateway/gateway_id`).

```python
from agentcore_tools import get_gateway_client

# Auto-loads gateway_id from SSM following the repository convention
gateway = get_gateway_client('dev')  # example context; see docs for exact usage
result = gateway.invoke_tool('check_warranty', {...})
```

**Parameters**:
- `agent_namespace` (str): Agent namespace (e.g., `app/myagent`)

**Returns**: Configured `GatewayClient` instance

---

### `memory.py` - Memory Helpers

**Purpose**: Store and retrieve conversation context via AgentCore Memory

#### Classes

##### `MemoryClient`
Client for AgentCore Memory operations.

```python
from agentcore_tools import MemoryClient

# Initialize client
memory = MemoryClient(
    memory_id='CustomerSupportMemory-abc123',  # Or from SSM
    region='us-east-1'
)

# Store short-term memory (conversation history)
memory.store_short_term(
    user_id='user-123',
    session_id='session-456',
    content={
        'role': 'user',
        'message': 'What is my warranty status?'
    },
    ttl_seconds=3600  # 1 hour
)

# Retrieve conversation history
history = memory.get_short_term(
    user_id='user-123',
    session_id='session-456'
)

# Store long-term memory (user preferences)
memory.store_long_term(
    user_id='user-123',
    memory_id='pref-language',
    content={'language': 'en-US'},
    category='preferences'
)
```

**Constructor Parameters**:
- `memory_id` (str): AgentCore Memory ID
- `region` (str): AWS region (default: `us-east-1`)

**Methods**:

##### `store_short_term(user_id: str, session_id: str, content: dict, ttl_seconds: int = 3600)`
Store short-term memory (conversation history).

**Parameters**:
- `user_id` (str): User identifier
- `session_id` (str): Session identifier
- `content` (dict): Memory content (conversation turn)
- `ttl_seconds` (int): Time-to-live in seconds (default: 1 hour)

---

##### `get_short_term(user_id: str, session_id: str, limit: int = 10) -> list[dict]`
Retrieve short-term memory (conversation history).

**Parameters**:
- `user_id` (str): User identifier
- `session_id` (str): Session identifier
- `limit` (int): Maximum number of entries to retrieve

**Returns**: List of memory entries (newest first)

---

##### `store_long_term(user_id: str, memory_id: str, content: dict, category: str = 'general')`
Store long-term memory (persistent user data).

**Parameters**:
- `user_id` (str): User identifier
- `memory_id` (str): Memory entry identifier
- `content` (dict): Memory content
- `category` (str): Memory category (e.g., `preferences`, `facts`, `history`)

---

##### `get_long_term(user_id: str, category: str = None) -> list[dict]`
Retrieve long-term memory.

**Parameters**:
- `user_id` (str): User identifier
- `category` (str, optional): Filter by category

**Returns**: List of long-term memory entries

---

##### `search_semantic(query: str, user_id: str = None, limit: int = 5) -> list[dict]`
Semantic search across memories.

```python
# Find relevant memories for query
results = memory.search_semantic(
    query='user preferences for product notifications',
    user_id='user-123',
    limit=5
)
```

**Parameters**:
- `query` (str): Search query
- `user_id` (str, optional): Filter to specific user
- `limit` (int): Maximum results

**Returns**: List of semantically similar memory entries

---

#### Helper Function

##### `get_memory_client(context: str) -> MemoryClient`
Create Memory client using SSM configuration (e.g., loads `/agentcore/{env}/memory/memory_id`).

```python
from agentcore_tools import get_memory_client

memory = get_memory_client('dev')  # example context; see docs for exact usage
```

---

## 🔧 Installation

### As Workspace Dependency (Recommended)

```bash
cd agents/customer-support
uv add agentcore-tools --workspace
```

Automatically adds:
```toml
dependencies = [
    "agentcore-common",  # Auto-included
    "agentcore-tools",
]

[tool.uv.sources]
agentcore-common = { workspace = true }
agentcore-tools = { workspace = true }
```

---

## 📖 Usage Examples

### Gateway Integration

```python
from agentcore_tools import get_gateway_client

# Initialize from SSM
gateway = get_gateway_client('app/myagent')

# Define tool wrapper
def check_product_warranty(product_id: str, serial_number: str) -> dict:
    """Check warranty status via Gateway tool."""
    return gateway.invoke_tool(
        tool_name='check_warranty',
        input_data={
            'product_id': product_id,
            'serial_number': serial_number
        }
    )

# Use in agent
result = check_product_warranty('LAPTOP-2024', 'SN123456')
print(f"Warranty expires: {result['expiration_date']}")
```

### Memory Integration

```python
from agentcore_tools import get_memory_client

memory = get_memory_client('app/myagent')

def chat_with_memory(user_id: str, session_id: str, message: str):
    # Retrieve conversation history
    history = memory.get_short_term(user_id, session_id, limit=10)

    # Process with agent
    response = agent.run(message, context=history)

    # Store new messages
    memory.store_short_term(
        user_id=user_id,
        session_id=session_id,
        content={'role': 'user', 'message': message}
    )
    memory.store_short_term(
        user_id=user_id,
        session_id=session_id,
        content={'role': 'assistant', 'message': response}
    )

    return response
```

---

## 🧪 Testing

### Unit Tests

```bash
cd packages/agentcore-tools
uv run pytest tests/ -v
```

---

## 🔗 Dependencies

- **agentcore-common**: Authentication, configuration, observability
- **boto3**: AWS SDK
- **bedrock-agentcore**: AgentCore SDK

---

## 📝 Development

### Adding New Tool Integrations

1. Add module to `src/agentcore_tools/`
2. Implement client class
3. Export in `__init__.py`
4. Add tests
5. Update README

### Updating Dependencies

```bash
cd packages/agentcore-tools
uv add <package-name>
uv lock  # Update workspace lockfile
```

---

## 🔗 Related Packages

- **agentcore-common**: Shared utilities (auth, config, observability)

---

## 📄 License

See [LICENSE](../../LICENSE) in repository root.
