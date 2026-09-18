# Security and Secret Handling

The project owner supplied an API key while describing the deployed Gateway. It is **not** included in this package.

## Required action

If that key is still active, rotate/revoke it immediately and create a new credential through the intended AWS AgentCore Token Vault / authentication configuration. Never place the replacement key in:

- `main.py`
- `.env.example`
- Git
- screenshots
- Markdown
- ZIP submissions
- shell history

Use environment injection, AWS Secrets Manager, AgentCore Token Vault, or the authentication mechanism required by the deployed Gateway.

## What is safe to include

The package includes non-secret resource identifiers such as:

- Region
- Gateway URL
- Knowledge Base ID
- Memory ID
- Lambda names
- API Gateway invoke URL
- IAM role ARN

Even these values should be reviewed against your course's submission policy before public posting.
