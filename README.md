# customer-support-AI-agent-

AI customer support agent using Amazon Bedrock AgentCore and the Strands SDK

## Project Information

- **Project:** AI Customer Support Agent
- **Developer:** Edris Abdella Nuure
- **Phone:** +251905131051
- **Email:** <edrisabdella178@gmail.com>
- **Repository:**
    <https://github.com/Edrisabdella/customer-support-AI-agent-.git>
- **AWS Region:** `us-east-1`
- **Primary Model:** `global.amazon.nova-2-lite-v1:0`
- **Framework:** Strands Agents
- **Platform:** Amazon Bedrock AgentCore
- **Protocol:** HTTP
- **Project:** AWS Future Engineers / Future AWS Agent Engineer ---
    Course 2, Project 2

------------------------------------------------------------------------

## Overview

The **AI Customer Support Agent** is an AWS-native conversational
customer-support system built with **Strands Agents**, **Amazon Bedrock
AgentCore Runtime**, **AgentCore Gateway**, **AgentCore Memory**,
**Amazon Bedrock Knowledge Bases**, **AgentCore Code Interpreter**, and
**AgentCore Browser**.

The agent is designed to handle realistic customer-support requests
including:

- Order-status and shipment tracking
- Customer and loyalty-profile lookup
- Refund processing and refund-status checks
- Return-label retrieval
- Knowledge-base questions using RAG
- Persistent customer facts and preferences
- Loyalty-point redemption and tier discounts
- Live browser interaction
- Multi-tool customer-support workflows

The project demonstrates how an AI agent can combine a foundation model
with enterprise tools, retrieval, persistent memory, deterministic code
execution, and browser automation.

------------------------------------------------------------------------

## Project Goals

1. Deploy an AI agent to Amazon Bedrock AgentCore Runtime.
2. Integrate business systems through MCP and AgentCore Gateway.
3. Implement Retrieval-Augmented Generation with a Bedrock Knowledge
    Base.
4. Persist and retrieve customer information with AgentCore Memory.
5. Use Code Interpreter for deterministic loyalty calculations.
6. Use AgentCore Browser for live web interaction.
7. Build a maintainable and testable customer-support architecture.
8. Demonstrate end-to-end agent workflows.

------------------------------------------------------------------------

## Architecture

``` text
Customer
   |
   v
Amazon Bedrock AgentCore Runtime
   |
   +--> Strands Agent + Amazon Nova
   |
   +--> AgentCore Gateway / MCP
   |       +--> Customer API
   |       +--> Order API
   |       +--> Refund Processor
   |       +--> Knowledge Base tools
   |
   +--> AgentCore Memory
   |       +--> Customer Facts
   |       +--> Customer Preferences
   |
   +--> Bedrock Knowledge Base
   |       +--> RAG retrieval
   |
   +--> AgentCore Code Interpreter
   |       +--> Loyalty calculations
   |
   +--> AgentCore Browser
           +--> Live web navigation
```

Amazon Bedrock AgentCore provides managed services for runtime hosting,
memory, Gateway/MCP integrations, code execution, and browser
automation.

------------------------------------------------------------------------

## Core Capabilities

## 1. AgentCore Runtime

The application uses `BedrockAgentCoreApp` as its runtime entry point.

The application follows the AgentCore Runtime pattern:

``` python
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

@app.entrypoint
async def invoke(payload):
    ...

if __name__ == "__main__":
    app.run()
```

### Runtime configuration

  Setting     Value
  ----------- -------------------------
  Project     `CustomerSupportDeploy`
  Runtime     `CustomerSupportAgent`
  Region      `us-east-1`
  Network     `PUBLIC`
  Protocol    `HTTP`
  Python      3.14
  Model       Amazon Nova 2 Lite
  Framework   Strands Agents

------------------------------------------------------------------------

## 2. MCP Gateway and Tools

The agent uses an MCP client to connect to an Amazon Bedrock AgentCore
Gateway.

### Gateway

``` text
https://customersupportgateway-uxvyatjhl6.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp
```

The Gateway exposes business functionality as MCP-compatible tools,
allowing the model to use structured enterprise operations instead of
inventing customer or order information.

### Verified Gateway tools

``` text
customer-support-order-tracker-api___get_customer
customer-support-order-tracker-api___get_customer_orders
customer-support-order-tracker-api___get_order
kb-target-vy1vuf___AgenticRetrieveStream
kb-target-vy1vuf___Retrieve
refund-processor___check_refund_status
refund-processor___get_return_label
refund-processor___initiate_refund
```

### Customer example

``` text
Customer ID: CUST-123
Customer: Jane Smith
Loyalty Points: 4250
Tier: Gold
```

### Order example

``` text
Order: ORD-001
Status: SHIPPED
Tracking: TRK987654321
Carrier: UPS
```

------------------------------------------------------------------------

# 3. Retrieval-Augmented Generation (RAG)

The application provides:

``` python
@tool
def search_knowledge_base(query: str) -> str:
    ...
```

The tool retrieves relevant content from an Amazon Bedrock Knowledge
Base.

### Knowledge Base

``` text
W6RC69EXD5
```

Retrieved chunks are combined with:

``` text
---
```

The workflow is:

``` text
User question
      |
      v
search_knowledge_base()
      |
      v
Bedrock Knowledge Base
      |
      v
Relevant chunks
      |
      v
Strands Agent
      |
      v
Grounded answer
```

The implementation also guards against an unavailable or unconfigured
Knowledge Base.

------------------------------------------------------------------------

## 4. AgentCore Memory

Persistent memory is implemented with Amazon Bedrock AgentCore Memory.

### Memory

``` text
CustomerSupportMemory-ECNYSn3F91
```

Configured strategies include:

``` text
customer_facts
customer_preferences
```

with namespaces associated with the customer actor.

The custom `MemoryHook`:

1. Determines available memory namespaces.
2. Retrieves relevant records across namespaces.
3. Identifies the strategy type.
4. Injects useful memory into the agent context.
5. Saves the latest user/assistant interaction using `create_event()`.
6. Enables cross-session recall.

### Example

Session A:

``` text
Hi, I am Jane. I prefer concise responses.
```

Later, Session B can ask:

``` text
What do you remember about me?
```

The agent can retrieve:

``` text
Name: Jane
Preference: concise responses
```

------------------------------------------------------------------------

## 5. Code Interpreter Loyalty Calculation

The loyalty workflow uses AgentCore Code Interpreter for deterministic
business calculations.

## Shipping rates

``` python
{
    "standard": 1,
    "device": 2,
    "fresh": 5
}
```

## Loyalty tiers

``` python
{
    "Silver": 0.00,
    "Gold": 0.10,
    "Platinum": 0.15
}
```

## Point conversion

``` text
100 points = $1
```

## Redemption rules

``` text
Minimum redemption: 500 points
Redemption increment: 500 points
Maximum redemption: 50% of order value
```

## Structured result

The calculation returns:

``` text
points_redeemed
tier_discount_pct
final_total
remaining_points
```

### Example

``` text
Tier: Gold
Points: 4250
Order: $150
Shipping: standard
```

Calculation:

``` text
Redeemed: 4000 points
Point value: $40
Remaining: 250 points
Subtotal after points: $110
Gold discount: 10%
Tier discount: $11
Final total: $99
```

The implementation also extracts explicit current-request values so that
the customer's current order amount, tier, points, and shipping category
take precedence over stale context.

------------------------------------------------------------------------

# 6. Browser Automation

The project integrates:

``` python
from strands_tools.browser import AgentCoreBrowser

browser_tool = AgentCoreBrowser(region=REGION)
```

and exposes:

``` python
browser_tool.browser
```

The browser workflow is designed to:

1. Detect an explicit browser request.
2. Start the AgentCore Browser tool.
3. Navigate to the requested URL.
4. Use the live browser rather than guessing.
5. Return information actually observed.
6. Minimize unnecessary browser actions.

Example:

``` text
Use the browser to visit https://www.amazon.com
and tell me the page title.
```

------------------------------------------------------------------------

# Customer Support Workflows

## Order Tracking

Example request:

``` text
Where is order ORD-001?
Please provide the shipping status, tracking number,
carrier, and estimated delivery date.
```

Verified result:

``` text
Status: SHIPPED
Tracking: TRK987654321
Carrier: UPS
Estimated Delivery: September 18, 2026
```

## Refund Processing

Example:

``` text
I want a refund for order ORD-002.
Please process the refund and tell me the refund ID
and expected processing time.
```

Verified result:

``` text
Refund ID: REF-097158AC
Status: APPROVED
Processing: 3–5 business days
```

## Loyalty Benefits

The agent can explain loyalty benefits including:

- 15% Platinum discount
- Priority support
- Enhanced shipping benefits
- Points earning
- Early-access benefits

Exact operational benefits should remain grounded in the configured
business data.

## Knowledge Base

Example:

``` text
What is the company's refund policy?
```

The agent can call:

``` text
search_knowledge_base()
```

before producing the answer.

------------------------------------------------------------------------

# Gateway Tools

## Customer

### `get_customer`

Retrieves customer information such as name, points, and tier.

### `get_customer_orders`

Retrieves a customer's order history.

### `get_order`

Retrieves detailed information about a specific order.

## Refund

### `initiate_refund`

Starts a refund workflow.

### `check_refund_status`

Checks an existing refund.

### `get_return_label`

Retrieves return-label information.

## Knowledge Base

Gateway Knowledge Base tools include:

``` text
Retrieve
AgenticRetrieveStream
```

The direct `Retrieve` path is used by the project's RAG workflow.

------------------------------------------------------------------------

# Memory Design

``` text
Actor
 |
 +-- customer_facts
 |      +-- cs_agent/{actorId}/facts
 |
 +-- customer_preferences
        +-- cs_agent/{actorId}/preferences
```

Customer facts can include durable account information.

Customer preferences can include communication preferences such as
concise responses.

The memory hook retrieves useful information before the response and
records the latest interaction afterward.

------------------------------------------------------------------------

# Security and IAM

The runtime uses an AWS IAM execution role.

The application requires permissions appropriate to its enabled
services.

Memory access required by the custom hook includes:

``` text
bedrock-agentcore:GetMemory
bedrock-agentcore:ListMemoryStrategies
bedrock-agentcore:RetrieveMemoryRecords
bedrock-agentcore:CreateEvent
```

Additional permissions are required for model invocation, Gateway
integrations, Knowledge Base retrieval, Code Interpreter, and Browser
according to the deployed configuration.

## Credential safety

Never commit:

``` text
AWS access keys
AWS secret keys
AWS session tokens
Private API keys
Passwords
Temporary credentials
```

Do not place credentials in:

``` text
main.py
README.md
pyproject.toml
agentcore.json
Git history
```

If credentials are exposed, revoke or rotate them immediately.

------------------------------------------------------------------------

# Technology Stack

  Technology                   Purpose
  ---------------------------- ------------------------------
  Python                       Application language
  Strands Agents               Agent orchestration
  Amazon Bedrock               Model inference
  Amazon Nova 2 Lite           Primary model
  AgentCore Runtime            Agent hosting
  AgentCore Gateway            MCP business tools
  MCP                          Tool interoperability
  AgentCore Memory             Persistent memory
  Bedrock Knowledge Base       RAG
  AgentCore Code Interpreter   Code execution
  AgentCore Browser            Browser automation
  Boto3                        AWS SDK
  Playwright                   Browser dependency
  AWS CLI                      AWS administration
  AgentCore CLI                Deployment
  uv                           Python dependency management
  PowerShell                   Windows development

------------------------------------------------------------------------

# Repository Structure

``` text
CustomerSupportDeploy/
|
+-- app/
|   +-- CustomerSupportAgent/
|       +-- main.py
|       +-- pyproject.toml
|       +-- README.md
|       +-- uv.lock
|       +-- .gitignore
|       +-- mcp_client/
|       +-- model/
|       +-- skills/
|
+-- agentcore/
|   +-- agentcore.json
|   +-- aws-targets.json
|
+-- README.md
```

The principal application is:

``` text
app/CustomerSupportAgent/main.py
```

------------------------------------------------------------------------

# Prerequisites

Install:

- Python 3.10+
- Node.js
- npm
- AWS CLI
- AWS credentials
- uv
- AgentCore CLI

The application uses packages including:

``` text
bedrock-agentcore
boto3
mcp
playwright
strands-agents
strands-agents-tools
aws-opentelemetry-distro
nest-asyncio
```

------------------------------------------------------------------------

## Installation

Clone:

``` powershell
git clone https://github.com/Edrisabdella/customer-support-AI-agent-.git
cd customer-support-AI-agent-
```

Install AgentCore CLI:

``` powershell
npm install -g @aws/agentcore
```

Synchronize Python dependencies:

``` powershell
uv sync
```

Verify Python:

``` powershell
uv run python --version
```

Verify AWS:

``` powershell
aws sts get-caller-identity
```

Verify AgentCore CLI:

``` powershell
agentcore --version
```

------------------------------------------------------------------------

# Configuration

Primary region:

``` text
us-east-1
```

Project resources:

``` text
Gateway:
https://customersupportgateway-uxvyatjhl6.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp

Memory:
CustomerSupportMemory-ECNYSn3F91

Knowledge Base:
W6RC69EXD5

Model:
global.amazon.nova-2-lite-v1:0
```

For portable deployments, prefer environment variables for
environment-specific configuration.

Example:

``` powershell
$env:AWS_REGION="us-east-1"
$env:AWS_DEFAULT_REGION="us-east-1"
```

------------------------------------------------------------------------

## Local Validation

Validate:

``` powershell
agentcore validate
```

Compile:

``` powershell
uv run python -m py_compile .pp\CustomerSupportAgent\main.py
```

Synchronize:

``` powershell
uv sync
```

Check Playwright:

``` powershell
uv run python -c "import playwright; print(playwright.__version__)"
```

------------------------------------------------------------------------

# Deployment

Validate first:

``` powershell
agentcore validate
```

Preview:

``` powershell
agentcore deploy --dry-run
```

Deploy:

``` powershell
agentcore deploy --yes
```

Check status:

``` powershell
agentcore status
```

View logs:

``` powershell
agentcore logs
```

------------------------------------------------------------------------
