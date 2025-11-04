"""Pytest fixtures for gateway custom resource tests.

Module-specific fixtures. Shared fixtures (aws_credentials, lambda_context, ssm_client, iam_client)
are available from ../conftest.py
"""

import json
from typing import Any

import pytest


@pytest.fixture
def gateway_role_arn(iam_client):
    """Create a mock IAM role for gateway."""
    response = iam_client.create_role(
        RoleName="test-gateway-role",
        AssumeRolePolicyDocument=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "bedrock.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                    }
                ],
            }
        ),
    )
    return response["Role"]["Arn"]


@pytest.fixture
def create_event(gateway_role_arn) -> dict[str, Any]:
    """CloudFormation CREATE event."""
    return {
        "RequestType": "Create",
        "ServiceToken": "arn:aws:lambda:us-east-1:123456789012:function:provisioner",
        "ResponseURL": "https://cloudformation-custom-resource-response.s3.amazonaws.com/test",
        "StackId": "arn:aws:cloudformation:us-east-1:123456789012:stack/test-stack/guid",
        "RequestId": "test-request-id-create",
        "LogicalResourceId": "BedrockGateway",
        "ResourceType": "Custom::BedrockGateway",
        "ResourceProperties": {
            "ServiceToken": "arn:aws:lambda:us-east-1:123456789012:function:provisioner",
            "GatewayName": "test-gateway",
            "GatewayRoleArn": gateway_role_arn,
            "Environment": "dev",
            "AgentNamespace": "test/namespace",
            "SSMPrefix": "/agentcore/dev/gateway",
        },
    }


@pytest.fixture
def update_event(create_event, gateway_role_arn) -> dict[str, Any]:
    """CloudFormation UPDATE event."""
    event = create_event.copy()
    event.update(
        {
            "RequestType": "Update",
            "RequestId": "test-request-id-update",
            "PhysicalResourceId": "test-gateway-id-12345",
            "OldResourceProperties": create_event["ResourceProperties"].copy(),
        }
    )
    # Change role ARN to simulate an update
    event["ResourceProperties"]["GatewayRoleArn"] = (
        f"{gateway_role_arn.rsplit(':', 1)[0]}:role/updated-gateway-role"
    )
    return event


@pytest.fixture
def delete_event(create_event) -> dict[str, Any]:
    """CloudFormation DELETE event."""
    event = create_event.copy()
    event.update(
        {
            "RequestType": "Delete",
            "RequestId": "test-request-id-delete",
            "PhysicalResourceId": "test-gateway-id-12345",
        }
    )
    return event


@pytest.fixture
def mock_bedrock_response():
    """Mock successful Bedrock Gateway API response."""
    return {
        "gatewayId": "test-gateway-id-12345",
        "gatewayName": "test-gateway",
        "gatewayArn": "arn:aws:bedrock:us-east-1:123456789012:gateway/test-gateway-id-12345",
        "status": "AVAILABLE",
        "createdAt": "2025-01-01T00:00:00Z",
        "updatedAt": "2025-01-01T00:00:00Z",
    }
