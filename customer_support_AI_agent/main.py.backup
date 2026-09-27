"""
Customer Support AI Agent
=========================
Production-ready agent for Amazon Bedrock AgentCore + Strands SDK.

Runs locally:
    uv run main.py '{"prompt": "Where is order ORD-001?", "customer_id": "CUST-123", "session_id": "s1"}'

Deploys to AgentCore:
    agentcore configure --entrypoint main.py --name customer_support_agent
    agentcore deploy
    agentcore invoke '{"prompt": "Hello", "customer_id": "CUST-123", "session_id": "s1"}'
"""

# ── Imports ───────────────────────────────────────────────────────────────────
from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.memory import MemoryClient
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamable_http_client

import argparse
import asyncio
import boto3
import json
import logging
import os
import uuid

from typing import Dict

from strands.hooks import (
    HookProvider,
    AfterInvocationEvent,
    HookRegistry,
    MessageAddedEvent,
)

from bedrock_agentcore.tools.code_interpreter_client import code_session

# Optional browser tool (import defensively)
try:
    from strands_tools.browser import AgentCoreBrowser
    _BROWSER_AVAILABLE = True
except Exception:  # pragma: no cover
    AgentCoreBrowser = None
    _BROWSER_AVAILABLE = False

# SigV4 signing for the IAM-protected Gateway
import httpx
import botocore.session
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest


logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("CSAI_Agent")


# ── TODO 1 — App Initialisation ───────────────────────────────────────────────
app = BedrockAgentCoreApp()

# Required in headless deployments (prevents interactive consent prompts).
os.environ["BYPASS_TOOL_CONSENT"] = "true"


# ── TODO 2 — Configuration ────────────────────────────────────────────────────
GATEWAY_URL = os.getenv(
    "GATEWAY_URL",
    "https://customersupportgateway-atzshdc3rh.gateway."
    "bedrock-agentcore.us-east-1.amazonaws.com/mcp",
)
KB_ID = os.getenv("KB_ID", "7I0DUHIZCU")
REGION = os.getenv("AWS_REGION", "us-east-1")
MEMORY_ID = os.getenv("MEMORY_ID", "customer_support_agent_mem-UYY9NNGNkf")


# ── TODO 3 — Model and Clients ────────────────────────────────────────────────
model_id = "global.amazon.nova-2-lite-v1:0"

model = BedrockModel(model_id=model_id)

memory_client = MemoryClient(region_name=REGION)

_bedrock_runtime = boto3.client("bedrock-agent-runtime", region_name=REGION)


# ── SigV4 Auth for IAM-protected Gateway ──────────────────────────────────────
class _SigV4HttpxAuth(httpx.Auth):
    """httpx auth class that signs every request with AWS SigV4."""

    def __init__(self, region: str, service: str = "bedrock-agentcore"):
        session = botocore.session.get_session()
        self.credentials = session.get_credentials()
        self.region = region
        self.service = service

    def auth_flow(self, request):
        # Buffer the body so the signature is computed over the exact bytes sent.
        body = request.read() if hasattr(request, "read") else request.content
        aws_req = AWSRequest(
            method=request.method,
            url=str(request.url),
            headers=dict(request.headers),
            data=body,
        )
        SigV4Auth(self.credentials, self.service, self.region).add_auth(aws_req)
        request.headers.update(dict(aws_req.headers))
        yield request


def _make_signed_http_client(region: str) -> httpx.AsyncClient:
    """Create an httpx client that signs every request with SigV4."""
    return httpx.AsyncClient(
        auth=_SigV4HttpxAuth(region),
        timeout=httpx.Timeout(120.0),
    )


# ── TODO 4 — Namespace Helper ─────────────────────────────────────────────────
def get_namespaces(mem_client: MemoryClient, memory_id: str) -> Dict:
    """
    Return a dict mapping strategy type → namespace template string,
    e.g. {"SEMANTIC": "cs_agent/{actorId}/facts",
          "USER_PREFERENCE": "cs_agent/{actorId}/preferences"}.
    """
    try:
        strategies = mem_client.get_memory_strategies(memory_id)
        result: Dict = {}
        for s in strategies:
            stype = s.get("type", "")
            namespaces = s.get("namespaces") or s.get("namespaceTemplates") or []
            if stype and namespaces:
                result[stype] = namespaces[0]
        if result:
            return result
    except Exception as e:
        logger.warning(f"get_memory_strategies failed ({e}); using defaults")

    # Fallback to the exact namespaces your project provisioned
    return {
        "SEMANTIC": "cs_agent/{actorId}/facts",
        "USER_PREFERENCE": "cs_agent/{actorId}/preferences",
    }


# ── TODO 5 — Memory Hook ──────────────────────────────────────────────────────
def _extract_text_from_message(msg) -> str:
    """Best-effort text extraction from a Strands message object."""
    if msg is None:
        return ""
    content = getattr(msg, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
            else:
                text = getattr(block, "text", None)
                if text:
                    parts.append(text)
        return "\n".join(p for p in parts if p)
    # Fallback attributes
    for attr in ("text", "output"):
        v = getattr(msg, attr, None)
        if isinstance(v, str):
            return v
    return ""


def _is_plain_user_text(msg) -> bool:
    """True if msg is a plain-text user message (not a tool result)."""
    role = getattr(msg, "role", None)
    if role != "user":
        return False
    content = getattr(msg, "content", None)
    if isinstance(content, str):
        return True
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                return False
            if getattr(block, "type", None) == "tool_result":
                return False
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                return True
            if getattr(block, "type", None) == "text":
                return True
    return False


class MemoryHook(HookProvider):
    """Long-term memory hook for the customer support agent."""

    def __init__(
        self,
        actor_id: str,
        session_id: str,
        memory_client: MemoryClient,
        memory_id: str,
    ):
        self.actor_id = actor_id
        self.session_id = session_id
        self.memory_client = memory_client
        self.memory_id = memory_id
        self.namespaces = get_namespaces(memory_client, memory_id)
        logger.info(f"MemoryHook namespaces: {self.namespaces}")

    # ── Retrieve ─────────────────────────────────────────────────────────────
    def retrieve_customer_context(self, event: MessageAddedEvent):
        """Retrieve relevant memories and prepend them to the user message."""
        try:
            messages = getattr(event.agent, "messages", []) or []
            if not messages:
                return
            last = messages[-1]
            if not _is_plain_user_text(last):
                return

            user_query = _extract_text_from_message(last).strip()
            if not user_query:
                return
            # Avoid double-prepending
            if user_query.startswith("Customer Context:"):
                return

            collected = []
            for strategy_type, ns_template in self.namespaces.items():
                try:
                    namespace = ns_template.format(actorId=self.actor_id)
                    memories = self.memory_client.retrieve_memories(
                        memory_id=self.memory_id,
                        namespace=namespace,
                        query=user_query,
                        top_k=5,
                    )
                except Exception as e:
                    logger.warning(f"Memory retrieve ({strategy_type}) failed: {e}")
                    continue

                # Normalize response shape across SDK versions
                items = []
                if isinstance(memories, dict):
                    items = (
                        memories.get("memories")
                        or memories.get("memoryRecords")
                        or memories.get("results")
                        or []
                    )
                elif isinstance(memories, list):
                    items = memories

                for m in items:
                    if isinstance(m, dict):
                        txt = m.get("text") or m.get("content") or m.get("memory", "")
                    else:
                        txt = (
                            getattr(m, "text", "")
                            or getattr(m, "content", "")
                            or getattr(m, "memory", "")
                        )
                    if txt:
                        collected.append(f"[{strategy_type}] {txt}")

            if not collected:
                return

            context_block = "Customer Context:\n" + "\n".join(collected)
            new_text = f"{context_block}\n\n{user_query}"

            # Replace the message content in-place
            try:
                if isinstance(getattr(last, "content", None), str):
                    last.content = new_text
                elif isinstance(getattr(last, "content", None), list):
                    for block in last.content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            block["text"] = new_text
                            break
            except Exception as e:
                logger.warning(f"Could not prepend memory context: {e}")

        except Exception as e:
            logger.warning(f"retrieve_customer_context error: {e}")

    # ── Save ─────────────────────────────────────────────────────────────────
    def save_support_interaction(self, event: AfterInvocationEvent):
        """Save the completed turn to memory after the agent responds."""
        try:
            messages = getattr(event.agent, "messages", []) or []
            if not messages:
                return

            user_query = None
            assistant_reply = None

            for m in reversed(messages):
                if assistant_reply is None and getattr(m, "role", None) == "assistant":
                    txt = _extract_text_from_message(m).strip()
                    if txt:
                        assistant_reply = txt
                if user_query is None and _is_plain_user_text(m):
                    txt = _extract_text_from_message(m).strip()
                    if txt:
                        user_query = txt
                if user_query and assistant_reply:
                    break

            if not (user_query and assistant_reply):
                return

            # Strip injected memory context for cleaner storage
            if user_query.startswith("Customer Context:"):
                parts = user_query.split("\n\n", 1)
                if len(parts) == 2:
                    user_query = parts[1].strip()

            self.memory_client.create_event(
                memory_id=self.memory_id,
                actor_id=self.actor_id,
                session_id=self.session_id,
                messages=[
                    (user_query, "USER"),
                    (assistant_reply, "ASSISTANT"),
                ],
            )
            logger.info(f"Saved interaction to memory for actor={self.actor_id}")

        except Exception as e:
            logger.warning(f"save_support_interaction error: {e}")

    # ── Register ─────────────────────────────────────────────────────────────
    def register_hooks(self, registry: HookRegistry) -> None:  # type: ignore
        """Register both memory callbacks."""
        try:
            registry.add_callback(MessageAddedEvent, self.retrieve_customer_context)
            registry.add_callback(AfterInvocationEvent, self.save_support_interaction)
        except AttributeError:
            # Older Strands API uses .on(...)
            registry.on(MessageAddedEvent, self.retrieve_customer_context)
            registry.on(AfterInvocationEvent, self.save_support_interaction)


# ── TODO 6 — Knowledge Base Tool ─────────────────────────────────────────────
@tool
def search_knowledge_base(query: str) -> str:
    """
    Search the Amazon product catalog and support knowledge base.
    Use this for product specifications, return policies, warranty
    information, loyalty program details, and order status definitions.

    Args:
        query: The question or topic to search for

    Returns:
        Relevant information retrieved from the knowledge base
    """
    if not KB_ID:
        return "Knowledge base not configured."

    try:
        resp = _bedrock_runtime.retrieve(
            knowledgeBaseId=KB_ID,
            retrievalQuery={"text": query},
        )
        results = resp.get("retrievalResults", [])
        if not results:
            return "No relevant information found in the knowledge base."

        chunks = []
        for r in results:
            text = (r.get("content") or {}).get("text", "")
            if text:
                chunks.append(text)

        if not chunks:
            return "No textual content found in the knowledge base."

        return "\n---\n".join(chunks)

    except Exception as e:
        logger.error(f"Knowledge Base retrieval error: {e}")
        return f"Error retrieving from knowledge base: {e}"


# ── TODO 7 — Loyalty Discount Tool (Code Interpreter) ────────────────────────
@tool
def calculate_loyalty_discount(
    loyalty_points: int,
    tier: str,
    order_total: float,
    product_category: str = "standard",
) -> str:
    """
    Calculate the loyalty discount for a customer order using the
    AgentCore Code Interpreter. Runs exact arithmetic in a secure sandbox.

    Args:
        loyalty_points:   Customer's current points balance
        tier:             Customer tier — Silver, Gold, or Platinum
        order_total:      Order total in USD
        product_category: standard, device, or fresh

    Returns:
        Full discount breakdown and final price (JSON string)
    """
    code = f"""
import json

loyalty_points = {int(loyalty_points)}
tier = "{tier}"
order_total = {float(order_total)}
product_category = "{product_category}"

earn_rates = {{"standard": 1, "device": 2, "fresh": 5}}
tier_rates = {{"Silver": 0.00, "Gold": 0.10, "Platinum": 0.15}}

earn_rate = earn_rates.get(product_category, 1)
tier_discount_pct = tier_rates.get(tier, 0.0)

# Points are worth $0.01 each; cap redemption at 50% of order.
max_redeemable_dollars = order_total * 0.5
max_redeemable_points = int(max_redeemable_dollars * 100)
usable_points = min(loyalty_points, max_redeemable_points)

# Floor to nearest 500
points_redeemed = (usable_points // 500) * 500

points_value = points_redeemed * 0.01
subtotal = order_total - points_value
tier_discount_amount = subtotal * tier_discount_pct
final_total = subtotal - tier_discount_amount
total_savings = points_value + tier_discount_amount
points_earned = int(final_total * earn_rate)
remaining_points = loyalty_points - points_redeemed + points_earned

result = {{
    "points_redeemed": points_redeemed,
    "tier_discount_pct": tier_discount_pct,
    "tier_discount_amount": round(tier_discount_amount, 2),
    "final_total": round(final_total, 2),
    "total_savings": round(total_savings, 2),
    "points_earned": points_earned,
    "remaining_points": remaining_points,
}}
print(json.dumps(result))
"""

    try:
        with code_session(REGION) as client:
            response = client.invoke(
                "executeCode",
                {
                    "code": code,
                    "language": "python",
                    "clearContext": True,
                },
            )

        # Extract the printed JSON from the response
        output_text = ""
        if isinstance(response, dict):
            for key in ("output", "result", "text", "stdout"):
                if key in response and isinstance(response[key], str):
                    output_text = response[key]
                    break
            if not output_text:
                events = response.get("events") or []
                for ev in events:
                    if isinstance(ev, dict):
                        t = ev.get("text") or ev.get("output") or ""
                        if t:
                            output_text = t
                            break

        if not output_text:
            output_text = str(response)

        # Find and validate the JSON object inside the output
        start = output_text.find("{")
        end = output_text.rfind("}")
        if start != -1 and end != -1 and end > start:
            json_str = output_text[start : end + 1]
            json.loads(json_str)  # validate
            return json_str

        return output_text

    except Exception as e:
        logger.warning(f"Code Interpreter failed, using fallback: {e}")

        # Fallback: tier discount only
        tier_rates = {"Silver": 0.00, "Gold": 0.10, "Platinum": 0.15}
        pct = tier_rates.get(tier, 0.0)
        discount = order_total * pct
        fallback = {
            "points_redeemed": 0,
            "tier_discount_pct": pct,
            "tier_discount_amount": round(discount, 2),
            "final_total": round(order_total - discount, 2),
            "total_savings": round(discount, 2),
            "points_earned": 0,
            "remaining_points": loyalty_points,
            "fallback": True,
        }
        return json.dumps(fallback)


# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
You are a professional Customer Support AI Agent for an e-commerce store.

You help customers with:
- Order tracking and status (use Gateway order tools)
- Customer account lookups (use Gateway customer tools)
- Refunds and returns (use Gateway refund tools)
- Product specs, return policies, warranty, loyalty tier benefits
  (use search_knowledge_base)
- Loyalty discount calculations (use calculate_loyalty_discount)
- Live web lookups (use the browser tool)

RULES
=====
1. Use Gateway tools for any real customer or order information.
2. Never invent order numbers, tracking numbers, refund IDs, or delivery dates.
3. If a tool fails, do not claim success.
4. Use search_knowledge_base for product specs, return policies, warranty,
   loyalty tier benefits, and order status definitions.
5. Use calculate_loyalty_discount for any discount math.
6. Be concise, professional, and friendly.
"""


# ── TODO 8 — Agent Entrypoint ─────────────────────────────────────────────────
@app.entrypoint
async def invoke(payload, context=None):
    """
    Main handler called by AgentCore for every incoming request.

    Expected payload keys:
      prompt      (str, required)
      customer_id (str, optional)
      session_id  (str, optional)
    """
    try:
        user_input = (
            payload.get("prompt")
            or payload.get("input")
            or payload.get("message")
            or ""
        )
        user_input = str(user_input).strip()
        if not user_input:
            return "Please provide a customer support question."

        actor_id = payload.get("customer_id", "anonymous")
        session_id = payload.get("session_id") or str(uuid.uuid4())

        # Instantiate memory hook
        memory_hook = MemoryHook(
            actor_id=actor_id,
            session_id=session_id,
            memory_client=memory_client,
            memory_id=MEMORY_ID,
        )

        # Local tools
        tools = [search_knowledge_base, calculate_loyalty_discount]

        # Optional browser tool
        if _BROWSER_AVAILABLE:
            try:
                browser = AgentCoreBrowser(region=REGION)
                tools.append(browser.browser)
            except Exception as e:
                logger.warning(f"Browser tool unavailable: {e}")

        async def _run(agent_tools):
            agent = Agent(
                model=model,
                tools=agent_tools,
                hooks=[memory_hook],
                system_prompt=SYSTEM_PROMPT,
            )
            if hasattr(agent, "invoke_async"):
                return await agent.invoke_async(user_input)
            return agent(user_input)

        # Try Gateway first; gracefully degrade if unavailable
        response = None
        try:
            async with _make_signed_http_client(REGION) as http_client:
                async with streamable_http_client(
                    GATEWAY_URL, http_client=http_client
                ) as (read_stream, write_stream, _):
                    async with MCPClient(read_stream, write_stream) as mcp_client:
                        gateway_tools = await mcp_client.list_tools()
                        logger.info(f"Loaded {len(gateway_tools)} Gateway tool(s)")
                        all_tools = tools + list(gateway_tools)
                        response = await _run(all_tools)
        except Exception as e:
            logger.warning(
                f"Gateway connection failed ({type(e).__name__}: {e}); "
                "running without Gateway tools"
            )
            response = await _run(tools)

        # Normalize the agent response to a plain string
        if response is None:
            return "I could not generate a response."

        if isinstance(response, str):
            return response

        output = getattr(response, "output", None)
        if output is not None:
            return str(output)

        msg = getattr(response, "message", None)
        if msg is not None:
            txt = _extract_text_from_message(msg)
            if txt:
                return txt

        return str(response)

    except Exception as e:
        logger.error(f"Invocation error: {type(e).__name__}: {e}")
        return f"An error occurred: {e}"


# ── CLI entry point ───────────────────────────────────────────────────────────
def main():
    """Run one invocation from the command line for local testing."""
    parser = argparse.ArgumentParser()
    parser.add_argument("payload", type=str)
    args = parser.parse_args()
    response = asyncio.run(invoke(json.loads(args.payload)))
    print(response)


if __name__ == "__main__":
    # Runtime mode (default for `agentcore deploy`):
    app.run()

    # Local CLI mode (uncomment the line below for local testing):
    # main()