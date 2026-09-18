# Deployment and Verification Runbook

This runbook is aligned to the uploaded project document and the real resources supplied by the project owner.

## 1. Environment

```powershell
$env:AWS_REGION="us-east-1"
$env:MODEL_ID="global.amazon.nova-2-lite-v1:0"
$env:GATEWAY_URL="https://customersupportgateway-uxvyatjhl6.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"
$env:KB_ID="W6RC69EXD5"
$env:MEMORY_ID="CustomerSupportMemory-ECNYSn3F91"
```

The project document has a model-version inconsistency: its environment setup mentions Amazon Nova Lite (`amazon.nova-lite-v1:0`), while the starter `main.py` explicitly specifies `global.amazon.nova-2-lite-v1:0`. This package preserves the starter's explicit model ID but makes it configurable through `MODEL_ID`. Verify the model available to the actual lab account before deployment.

## 2. Verify AWS identity

```powershell
aws sts get-caller-identity
aws configure get region
```

Expected account: `601661065684`; expected region: `us-east-1`.

## 3. Verify the Gateway

```powershell
agentcore status
```

Then use MCP Inspector:

```powershell
npx @modelcontextprotocol/inspector
```

Connect to:

```text
https://customersupportgateway-uxvyatjhl6.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp
```

Confirm that the Gateway exposes the order-tracking API tools and refund Lambda tools. AWS documents MCP tool discovery/calls through the `/mcp` endpoint and `MCPClient`/streamable HTTP transport. See the official Gateway docs in the root README.

## 4. Install dependencies

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -U pip
pip install -e .
```

For a `uv` workflow:

```powershell
uv sync
```

## 5. Local syntax validation

```powershell
python -m py_compile agent/main.py lambda/order_tracker.py lambda/refund_processor.py
```

## 6. Configure AgentCore Runtime

From the `agent/` directory:

```powershell
agentcore configure --entrypoint main.py --name customer-support-ai-agent
agentcore deploy --dry-run
agentcore deploy
agentcore status
```

AWS's current AgentCore CLI workflow documents `agentcore dev`, `agentcore deploy`, `agentcore deploy --dry-run`, `agentcore status`, and `agentcore invoke`. The deployment creates a Runtime endpoint and CloudWatch observability configuration. See the AWS Runtime CLI guide linked in the root README.

## 7. Invoke the deployed agent

```powershell
agentcore invoke '{"prompt":"Hello, what can you help me with?","customer_id":"CUST-123","session_id":"smoke-001"}'
```

Do not treat a command that merely starts without an error as full rubric proof. Capture the response as evidence.

## 8. CloudWatch

1. Open CloudWatch → Log groups.
2. Find the log group associated with the AgentCore Runtime deployment.
3. Create an `ERROR` metric filter.
4. Create an alarm for **more than 5 errors in 5 minutes**.
5. Capture the alarm configuration and a log/metric view for the submission.

The uploaded project document explicitly requires the CloudWatch alarm screenshot.
