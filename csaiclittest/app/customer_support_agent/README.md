# Customer Support AI Agent — Submission Package

**Project:** Building a Production-Grade Customer Support AI Agent with Amazon Bedrock AgentCore and the Strands SDK  
**Region:** `us-east-1`  
**Status:** Submission-ready implementation + real AWS resource manifest

## What is included

- Completed `agent/main.py` implementing all eight starter TODO areas required by the rubric.
- Lambda implementations for `order-tracker` and `refund-processor`.
- AgentCore Gateway MCP integration.
- Amazon Bedrock Knowledge Base retrieval tool.
- AgentCore Memory retrieval + persistence hook.
- AgentCore Code Interpreter loyalty calculator.
- AgentCore Browser integration.
- Product/support catalog used by the Knowledge Base.
- Exact resource IDs/endpoints supplied from the deployed AWS environment.
- Detailed deployment, verification, test, CloudWatch, security, and submission guides.
- Rubric traceability matrix.
- Professional architecture diagram using the real resource identifiers supplied by the project owner.
- No AWS API keys or other credentials are stored in the package.

## Important evidence note

The rubric requires six successful `agentcore invoke` test outputs and a CloudWatch alarm screenshot. This package contains the exact commands, expected behavior, evidence naming convention, and real-resource configuration, but it does **not** fabricate test logs or screenshots that were not actually captured. Put the real outputs under `submission/evidence/` after running the commands in `submission/TEST_EVIDENCE.md`.

The project document explicitly requires screenshots/terminal output for Tests 1–6 and a CloudWatch alarm screenshot. Those are grading evidence, not code artifacts.

## Quick start

1. Copy `.env.example` values into your shell environment.
2. Install dependencies with your preferred Python environment / `uv`.
3. Verify AWS identity and the deployed resources.
4. Run `agentcore status` and `agentcore invoke`.
5. Capture all six test outputs.
6. Verify/configure the CloudWatch error alarm.
7. Put the evidence files in `submission/evidence/`.
8. Submit this ZIP.

### Official documentation

- [Amazon Bedrock AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/)
- [AgentCore Runtime CLI](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-cli.html)
- [AgentCore Gateway](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-using.html)
- [AgentCore Gateway + Strands](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-agent-integration.html)
- [AgentCore Memory](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agentcore-sdk-memory.html)
- [Memory strategies](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-strategies.html)
- [AgentCore Code Interpreter](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/code-interpreter-building-agents.html)
- [AgentCore Browser](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/browser-tool.html)
- [Strands Agents](https://strandsagents.com/)
- [MCP Inspector](https://github.com/modelcontextprotocol/inspector)
- [uv](https://docs.astral.sh/uv/)
- [Udacity starter repository](https://github.com/udacity/cd14763-project-starter/)
