# Real AWS Resource Manifest

This file records the resource information supplied by the project owner. It is intended to make the submission auditable without storing credentials.

**Captured from AWS console information supplied on 11 September 2026.** Resource status can change; verify current status immediately before submission.

## Account / Region

- AWS account ID: `601661065684`
- Region: `us-east-1` (N. Virginia)

## Lambda — order-tracker

- Function: `order-tracker`
- Runtime: Python 3.12
- Handler: `lambda_function.lambda_handler`
- Architecture: x86_64
- Package size: 2.2 kB
- Code storage mode: Copy (default)
- S3 snapshot: `arn:aws:s3:::prod-04-2014-tasks/snapshots/601661065684/order_tracker-b8d685cb-000a-463e-a174-3657c2e82707`
- Runtime version ARN: `arn:aws:lambda:us-east-1::runtime:c1ab740f3656a72d7917665a940f8634df245489445f5a660de5a634d06c5433`
- SHA256: `4pFwZDNUqZQmeWpjX4WqROQ5Y/NTbvCfjeI8Vgcggxw=`

Console: https://us-east-1.console.aws.amazon.com/lambda/home?region=us-east-1#/functions/order-tracker

## Lambda — refund-processor

- Function: `refund-processor`
- Runtime: Python 3.12
- Handler: `lambda_function.lambda_handler`
- Architecture: x86_64
- Package size: 1.8 kB
- Code storage mode: Copy (default)
- S3 snapshot: `arn:aws:s3:::prod-04-2014-tasks/snapshots/601661065684/refund_processor-bd6a6912-1510-4f47-8a05-b8562bacc7f6`
- Runtime version ARN: `arn:aws:lambda:us-east-1::runtime:c1ab740f3656a72d7917665a940f8634df245489445f5a660de5a634d06c5433`
- SHA256: `z/eGtF5geMYq+KnXAx1ox7sO2Py3Uy7ZD9pFJSeiEyk=`

Console: https://us-east-1.console.aws.amazon.com/lambda/home?region=us-east-1#/functions/refund-processor

## API Gateway — order tracking REST API

- Invoke URL: `https://mgkmuc0e6g.execute-api.us-east-1.amazonaws.com/dev`
- Required routes from the project rubric:
  - `GET /orders/{order_id}`
  - `GET /customers/{customer_id}/orders`
  - `GET /customers/{customer_id}`

API endpoint: https://mgkmuc0e6g.execute-api.us-east-1.amazonaws.com/dev

## AgentCore Gateway

- Name: `CustomerSupportGateway`
- Gateway ID: `customersupportgateway-uxvyatjhl6`
- Status at capture: `Ready`
- Resource ARN: `arn:aws:bedrock-agentcore:us-east-1:601661065684:gateway/customersupportgateway-uxvyatjhl6`
- MCP endpoint: `https://customersupportgateway-uxvyatjhl6.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp`
- IAM role: `arn:aws:iam::601661065684:role/service-role/AmazonBedrockAgentCoreGatewayDefaultServiceRole1788819795533`
- Expected targets:
  - `order-tracker` — API Gateway-backed order lookup
  - `refund-processor` — direct Lambda-backed refund/return tools

Console: https://us-east-1.console.aws.amazon.com/bedrock-agentcore/home?region=us-east-1#/gateways

## AgentCore Memory

- Name / ID: `CustomerSupportMemory-ECNYSn3F91`
- ARN: `arn:aws:bedrock-agentcore:us-east-1:601661065684:memory/CustomerSupportMemory-ECNYSn3F91`
- Event expiration: 90 days
- Description: Memory for the Customer Support AI Agent
- Status at capture: `Creating`
- Creation date: 9 September 2026
- Required strategies from the project:
  - `customer_facts` → `cs_agent/{actorId}/facts`
  - `customer_preferences` → `cs_agent/{actorId}/preferences`

Console: https://us-east-1.console.aws.amazon.com/bedrock-agentcore/home?region=us-east-1#/memories

## Knowledge Base

- Name: `CustomerSupportKB`
- Knowledge Base ID: `W6RC69EXD5`
- Status at capture: `Available`
- Type: Managed vector store
- Embeddings: `amazon.titan-embed-text-v2:0`
- Embedding type: FLOAT32
- Vector dimensions: 1024
- Service role: `AmazonBedrockExecutionRoleForKnowledgeBase_t7lj6`
- Data source: product/support catalog uploaded to S3
- Vector store: OpenSearch Serverless (per project setup)
- Created: 9 September 2026, 01:58 UTC+03:00

Console: https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/knowledge-bases

## AgentCore Runtime / deployment

The supplied AWS resource details did not include the final deployed Runtime ARN or deployment name. The source project requires `agentcore deploy`, `agentcore status`, and successful `agentcore invoke`. Do not invent a Runtime ARN. Use:

```powershell
agentcore status
```

Runtime console: https://us-east-1.console.aws.amazon.com/bedrock-agentcore/home?region=us-east-1

## CloudWatch

The project rubric requires an ERROR metric filter and an alarm when error count exceeds 5 in a 5-minute window. The supplied resource details did not include a final alarm ARN/name, so none is invented here.

CloudWatch console: https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1

## Credential exclusion

The API key pasted in the conversation is intentionally omitted. It must not be committed to source control, Markdown, `.env`, screenshots, or the submission ZIP. Rotate it if it is still active.
