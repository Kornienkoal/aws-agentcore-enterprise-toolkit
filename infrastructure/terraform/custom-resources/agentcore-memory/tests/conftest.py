"""Pytest fixtures for memory custom resource tests.

Module-specific fixtures. Shared fixtures (aws_credentials, lambda_context, ssm_client)
are available from ../conftest.py
"""

from typing import Any

import pytest


@pytest.fixture
def create_event() -> dict[str, Any]:
    """CloudFormation CREATE event for memory."""
    return {
        "RequestType": "Create",
        "ServiceToken": "arn:aws:lambda:us-east-1:123456789012:function:provisioner",
        "ResponseURL": "https://cloudformation-custom-resource-response.s3.amazonaws.com/test",
        "StackId": "arn:aws:cloudformation:us-east-1:123456789012:stack/test-stack/guid",
        "RequestId": "test-request-id-create",
        "LogicalResourceId": "BedrockMemory",
        "ResourceType": "Custom::BedrockMemory",
        "ResourceProperties": {
            "ServiceToken": "arn:aws:lambda:us-east-1:123456789012:function:provisioner",
            "MemoryName": "test-memory",
            "MemoryStrategies": [
                {
                    "type": "userPreferenceMemoryStrategy",
                    "maxRecords": 1000,
                },
                {
                    "type": "semanticMemoryStrategy",
                    "maxRecords": 5000,
                },
            ],
            "Environment": "dev",
            "AgentNamespace": "test/namespace",
            "SSMPrefix": "/agentcore/dev/memory",
        },
    }


@pytest.fixture
def update_event(create_event) -> dict[str, Any]:
    """CloudFormation UPDATE event for memory."""
    event = create_event.copy()
    event.update(
        {
            "RequestType": "Update",
            "RequestId": "test-request-id-update",
            "PhysicalResourceId": "test-memory-id-12345",
            "OldResourceProperties": create_event["ResourceProperties"].copy(),
        }
    )
    # Change max records to simulate an update
    event["ResourceProperties"]["MemoryStrategies"][0]["maxRecords"] = 2000
    return event


@pytest.fixture
def delete_event(create_event) -> dict[str, Any]:
    """CloudFormation DELETE event for memory."""
    event = create_event.copy()
    event.update(
        {
            "RequestType": "Delete",
            "RequestId": "test-request-id-delete",
            "PhysicalResourceId": "test-memory-id-12345",
        }
    )
    return event


@pytest.fixture
def mock_bedrock_memory_response():
    """Mock successful Bedrock Memory API response."""
    return {
        "memoryId": "test-memory-id-12345",
        "memoryName": "test-memory",
        "memoryArn": "arn:aws:bedrock:us-east-1:123456789012:memory/test-memory-id-12345",
        "status": "AVAILABLE",
        "createdAt": "2025-01-01T00:00:00Z",
        "updatedAt": "2025-01-01T00:00:00Z",
        "memoryStrategies": [
            {"type": "userPreferenceMemoryStrategy", "maxRecords": 1000},
            {"type": "semanticMemoryStrategy", "maxRecords": 5000},
        ],
    }
