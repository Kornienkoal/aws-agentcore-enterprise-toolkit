FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim
WORKDIR /app

# All environment variables in one layer
ENV UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_NO_PROGRESS=1 \
    PYTHONUNBUFFERED=1 \
    DOCKER_CONTAINER=1 \
    AWS_REGION=us-east-1 \
    AWS_DEFAULT_REGION=us-east-1

# Install third-party dependencies for the agent
COPY agents/warranty-docs/requirements.txt requirements.txt
RUN uv pip install -r requirements.txt

# Install workspace packages from source without vendoring wheels
COPY packages/agentcore-common /tmp/packages/agentcore-common
COPY packages/agentcore-tools /tmp/packages/agentcore-tools
RUN uv pip install /tmp/packages/agentcore-common \
    && uv pip install /tmp/packages/agentcore-tools \
    && rm -rf /tmp/packages/agentcore-common /tmp/packages/agentcore-tools

RUN uv pip install aws-opentelemetry-distro>=0.10.1

# Signal that this is running in Docker for host binding logic
ENV DOCKER_CONTAINER=1

# Create non-root user
RUN useradd -m -u 1000 bedrock_agentcore
USER bedrock_agentcore

EXPOSE 9000
EXPOSE 8000
EXPOSE 8080

# Copy agent source into the image
COPY agents/warranty-docs/ ./

# Copy shared agent configuration from the repository root
COPY agent-config/warranty-docs.yaml agent-config/warranty-docs.yaml

# Use the full module path
CMD ["opentelemetry-instrument", "python", "-m", "runtime"]
