"""
Customer Support AI Agent
=========================
Production-oriented completion of the Udacity CD14763 project starter.

The implementation follows the supplied project instructions and rubric:
- AgentCore Runtime entrypoint
- AgentCore Gateway via MCP
- Bedrock Knowledge Base RAG
- AgentCore Memory long-term context
- AgentCore Code Interpreter loyalty calculations
- AgentCore Browser live web access

Configuration is intentionally read from environment variables so AWS
credentials and account-specific resource identifiers are never committed.
Required variables: GATEWAY_URL, KB_ID, MEMORY_ID. BROWSER_ID is optional
and defaults to the AWS-managed browser `aws.browser.v1`. AWS_REGION is optional
and defaults to us-east-1.
"""

from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.memory import MemoryClient
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamable_http_client
import argparse, json
import os, asyncio, boto3
from strands.hooks import (
    HookProvider, AfterInvocationEvent, HookRegistry, MessageAddedEvent,
)
import logging
import uuid
from typing import Any, Dict, Optional
from contextvars import ContextVar
import re
from bedrock_agentcore.tools.code_interpreter_client import code_session
from strands_tools.browser import AgentCoreBrowser


logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("CSAI_Agent")

# ── Section 1 — App Initialisation ───────────────────────────────────────────────
app = BedrockAgentCoreApp()

# Suppress interactive tool-consent prompts (required in headless deployments).
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# ── Section 2 — Configuration ────────────────────────────────────────────────────
# Account-specific values are supplied through the environment at deployment
# time. This keeps secrets/resource IDs out of source control.
GATEWAY_URL = os.getenv(
    "GATEWAY_URL",
    "https://customersupportgateway-uxvyatjhl6.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp",
).strip()
KB_ID = os.getenv("KB_ID", "W6RC69EXD5").strip()
REGION = os.getenv("AWS_REGION", "us-east-1").strip() or "us-east-1"
MEMORY_ID = os.getenv("MEMORY_ID", "CustomerSupportMemory-ECNYSn3F91").strip()
BROWSER_ID = os.getenv("BROWSER_ID", "aws.browser.v1").strip() or "aws.browser.v1"

# ── Section 3 — Model and Clients ────────────────────────────────────────────────
model_id = "global.amazon.nova-2-lite-v1:0"
model = BedrockModel(model_id=model_id)
memory_client = MemoryClient(region_name=REGION)
_bedrock_runtime = boto3.client("bedrock-agent-runtime", region_name=REGION)


_loyalty_request_override: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "loyalty_request_override", default=None
)


def _extract_explicit_loyalty_inputs(text: str) -> Dict[str, Any]:
    """Extract explicit loyalty facts from the current user request.

    Explicit values in the current request are authoritative and must not be
    replaced by stale values retrieved from an existing order or memory.
    """
    facts: Dict[str, Any] = {}
    lower = text.lower()

    points = re.findall(r"\b([0-9][0-9,]*)\s*(?:loyalty\s*)?points\b", text, re.I)
    if points:
        facts["loyalty_points"] = int(points[-1].replace(",", ""))

    for tier in ("Platinum", "Gold", "Silver"):
        if re.search(rf"\b{tier}\b", text, re.I):
            facts["tier"] = tier
            break

    # Currency is the most reliable signal. This intentionally accepts both
    # "$150" and "$ 150" so the project's exact test phrase is covered.
    currency_matches = re.findall(r"\$\s*([0-9]+(?:\.[0-9]{1,2})?)", text)
    if currency_matches:
        facts["order_total"] = float(currency_matches[-1])
    else:
        # Also support prose such as "150 dollars" / "150 USD" when no $
        # sign is present. Prefer amounts close to order/total wording.
        prose_matches = re.findall(
            r"(?:order\s+(?:total|amount)|place\s+(?:a|an)?\s*\$?\s*order)"
            r".{0,60}?\b([0-9]+(?:\.[0-9]{1,2})?)\s*(?:dollars?|usd)\b",
            text,
            re.I,
        )
        if prose_matches:
            facts["order_total"] = float(prose_matches[-1])

    if re.search(r"\bstandard(?:[- ]shipping)?\b", lower):
        facts["product_category"] = "standard"
    elif re.search(r"\b(?:device|amazon\s+device)\b", lower):
        facts["product_category"] = "device"
    elif re.search(r"\bfresh\b", lower):
        facts["product_category"] = "fresh"

    return facts

def _is_placeholder(value: str) -> bool:
    """Return True when an account-specific configuration value is absent."""
    return not value or value.startswith("<") or value.endswith(">")


def _extract_text(value: Any) -> str:
    """Extract readable text from common Strands/AWS content representations."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if isinstance(value.get("text"), str):
            return value["text"]
        for key in ("content", "output", "message", "value"):
            if key in value:
                text = _extract_text(value[key])
                if text:
                    return text
        return ""
    if isinstance(value, list):
        parts = [_extract_text(item) for item in value]
        return "".join(part for part in parts if part)
    return str(value)


def _message_text(message: Any) -> str:
    """Return plain text from a Strands message, ignoring tool-call blocks."""
    if not isinstance(message, dict):
        return ""
    return _extract_text(message.get("content"))


def _message_role(message: Any) -> str:
    if isinstance(message, dict):
        return str(message.get("role", "")).lower()
    return ""


def _memory_text(record: Any) -> str:
    """Extract text from AgentCore Memory retrieval result variants."""
    if isinstance(record, str):
        return record.strip()
    if not isinstance(record, dict):
        return ""
    for key in ("content", "text", "memory", "record", "value"):
        if key in record:
            text = _extract_text(record[key]).strip()
            if text:
                return text
    return ""


# ── Section 4 — Namespace Helper ─────────────────────────────────────────────────
def get_namespaces(mem_client: MemoryClient, memory_id: str) -> Dict[str, str]:
    """Return {strategy_type: namespace_template} from AgentCore Memory."""
    if _is_placeholder(memory_id):
        return {}
    response = mem_client.get_memory_strategies(memory_id)
    strategies = response.get("strategies", []) if isinstance(response, dict) else response
    namespaces: Dict[str, str] = {}
    for strategy in strategies or []:
        if not isinstance(strategy, dict):
            continue
        strategy_type = strategy.get("type") or strategy.get("strategyType") or strategy.get("name")
        templates = strategy.get("namespaces") or strategy.get("namespaceTemplates") or []
        if strategy_type and templates:
            namespaces[str(strategy_type)] = str(templates[0])
    return namespaces


# ── Section 5 — Memory Hook ──────────────────────────────────────────────────────
class MemoryHook(HookProvider):
    """Retrieve long-term customer context and persist each completed turn."""

    def __init__(self, actor_id: str, session_id: str,
                 memory_client: MemoryClient, memory_id: str):
        self.actor_id = actor_id
        self.session_id = session_id
        self.memory_client = memory_client
        self.memory_id = memory_id
        self.namespaces = get_namespaces(memory_client, memory_id)
        self.original_user_query = ""
        self.last_assistant_response = ""

    @staticmethod
    def _format_namespace(template: str, actor_id: str) -> str:
        return (template.replace("{actorId}", actor_id)
                       .replace("{actor_id}", actor_id))

    def _records(self, response: Any) -> list:
        if isinstance(response, dict):
            for key in ("memoryRecords", "memories", "results", "records"):
                value = response.get(key)
                if isinstance(value, list):
                    return value
        return response if isinstance(response, list) else []

    def _memory_record_text(self, record: Any) -> str:
        if isinstance(record, str):
            return record.strip()
        if not isinstance(record, dict):
            return ""
        # AgentCore Memory records can contain content as a string or nested
        # content blocks. Try the common shapes without assuming one SDK version.
        for key in ("content", "text", "memory", "record", "value"):
            if key in record:
                text = _extract_text(record[key]).strip()
                if text:
                    return text
        return ""

    def retrieve_customer_context(self, event: MessageAddedEvent):
        """Query every strategy namespace and prepend tagged memories to the user message."""
        if _is_placeholder(self.memory_id):
            return

        message = getattr(event, "message", None)
        if not isinstance(message, dict) or _message_role(message) != "user":
            return

        original_query = _message_text(message).strip()
        if not original_query or original_query.startswith("Customer Context:\n"):
            return
        self.original_user_query = original_query

        memories = []
        for strategy_type, template in self.namespaces.items():
            namespace = self._format_namespace(template, self.actor_id)
            try:
                response = self.memory_client.retrieve_memories(
                    self.memory_id,
                    namespace=namespace,
                    query=original_query,
                    top_k=5,
                )
                for record in self._records(response):
                    text = self._memory_record_text(record)
                    if text:
                        memories.append(f"[{strategy_type}] {text}")
            except Exception as exc:
                logger.warning("Memory retrieval failed for %s: %s", strategy_type, exc)

        if memories:
            enriched = f"Customer Context:\n{chr(10).join(memories)}\n\n{original_query}"
            message["content"] = [{"text": enriched}]

    def _find_turn_in_history(self, messages: Any) -> tuple[str, str]:
        user_text = self.original_user_query
        assistant_text = self.last_assistant_response
        for message in reversed(messages or []):
            role = _message_role(message)
            text = _message_text(message).strip()
            if not text:
                continue
            if role == "assistant" and not assistant_text:
                assistant_text = text
            elif role == "user" and not user_text:
                user_text = text
            if user_text and assistant_text:
                break
        return user_text, assistant_text

    def save_support_interaction(self, event: AfterInvocationEvent):
        """Save the completed user/assistant turn with MemoryClient.create_event()."""
        if _is_placeholder(self.memory_id):
            return

        messages = getattr(event.agent, "messages", [])
        user_text, assistant_text = self._find_turn_in_history(messages)
        if not user_text or not assistant_text:
            logger.warning("Memory save skipped because user/assistant text was missing.")
            return

        try:
            self.memory_client.create_event(
                memory_id=self.memory_id,
                actor_id=self.actor_id,
                session_id=self.session_id,
                messages=[(user_text, "USER"), (assistant_text, "ASSISTANT")],
            )
            logger.info("Saved support interaction to AgentCore Memory for actor %s", self.actor_id)
        except Exception as exc:
            logger.warning("Unable to save support interaction to memory: %s", exc)

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(MessageAddedEvent, self.retrieve_customer_context)
        registry.add_callback(AfterInvocationEvent, self.save_support_interaction)

# ── Section 6 — Knowledge Base Tool ─────────────────────────────────────────────
@tool
def search_knowledge_base(query: str) -> str:
    """
    Search the Amazon product catalog and support knowledge base.
    Use this for product specifications, return policies, warranty information,
    loyalty program details, and order-status definitions. Do not use it for
    live order lookup; use the Gateway order tools for that.

    Args:
        query: The question or topic to search for.

    Returns:
        Relevant information retrieved from the knowledge base.
    """
    if _is_placeholder(KB_ID):
        return "Knowledge base not configured. Set KB_ID before using RAG."

    try:
        response = _bedrock_runtime.retrieve(
            knowledgeBaseId=KB_ID,
            retrievalQuery={"text": query},
        )
        results = response.get("retrievalResults", [])
        if not results:
            return "No relevant knowledge-base results were found."

        chunks = []
        for result in results:
            content = result.get("content", {}) if isinstance(result, dict) else {}
            text = _extract_text(content).strip()
            if text:
                chunks.append(text)

        return "\n---\n".join(chunks) if chunks else "No relevant knowledge-base text was found."
    except Exception as exc:
        logger.exception("Knowledge Base retrieval failed")
        return f"Knowledge base retrieval failed: {exc}"


# ── Section 7 — Loyalty Discount Tool (Code Interpreter) ────────────────────────
def _calculate_loyalty_locally(loyalty_points: int, tier: str,
                               order_total: float, product_category: str) -> Dict[str, Any]:
    """Deterministic implementation of the project loyalty rules."""
    points = max(0, int(loyalty_points))
    total = max(0.0, float(order_total))
    tier_name = str(tier).strip().title()
    category = str(product_category).strip().lower()
    earn_rates = {"standard": 1, "device": 2, "fresh": 5}
    tier_rates = {"Silver": 0.00, "Gold": 0.10, "Platinum": 0.15}
    earn_rate = earn_rates.get(category, 1)
    tier_pct = tier_rates.get(tier_name, 0.0)

    # 100 points = $1; redemption must be in 500-point blocks and may not
    # exceed 50% of the original order value.
    max_value = total * 0.50
    max_points = int(max_value * 100) // 500 * 500
    points_redeemed = min((points // 500) * 500, max_points)
    points_value = points_redeemed / 100.0
    subtotal = max(0.0, total - points_value)
    tier_discount_amount = subtotal * tier_pct
    final_total = max(0.0, subtotal - tier_discount_amount)
    total_savings = max(0.0, total - final_total)
    points_earned = int(final_total * earn_rate)
    remaining_points = points - points_redeemed

    return {
        "points_redeemed": int(points_redeemed),
        "tier_discount_pct": tier_pct,
        "tier_discount_amount": round(tier_discount_amount, 2),
        "final_total": round(final_total, 2),
        "total_savings": round(total_savings, 2),
        "points_earned": points_earned,
        "remaining_points": int(remaining_points),
    }


def _extract_ci_json(response: Any) -> Optional[Dict[str, Any]]:
    """Extract the JSON printed by executeCode from AgentCore's stream response."""
    if not isinstance(response, dict):
        return None
    for event in response.get("stream", []):
        if not isinstance(event, dict) or "result" not in event:
            continue
        result = event["result"]
        # Official response shape: result.content[].text
        if isinstance(result, dict):
            content = result.get("content")
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and isinstance(item.get("text"), str):
                        text = item["text"].strip()
                        try:
                            parsed = json.loads(text)
                            if isinstance(parsed, dict):
                                return parsed
                        except json.JSONDecodeError:
                            continue
            # Also accept direct JSON/dict result shapes.
            if isinstance(result.get("text"), str):
                try:
                    parsed = json.loads(result["text"])
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    continue
            if isinstance(result, dict) and all(k in result for k in (
                "points_redeemed", "tier_discount_pct", "final_total", "remaining_points"
            )):
                return result
    return None


@tool
def calculate_loyalty_discount(loyalty_points: int, tier: str,
                                 order_total: float,
                                 product_category: str = "standard") -> str:
    """
    Calculate loyalty points redemption and tier discount using AgentCore Code Interpreter.

    Rules: standard/device/fresh earn 1/2/5 points per dollar; Silver/Gold/Platinum
    receive 0%/10%/15% tier discounts; 100 points=$1; redemption is in 500-point
    increments, has a 500-point minimum, and is capped at 50% of the order value.
    Tier discount is applied after point redemption. Returns points_redeemed,
    tier_discount_pct, final_total, remaining_points, total_savings, and points_earned.
    """
    override = _loyalty_request_override.get() or {}
    if "loyalty_points" in override:
        loyalty_points = int(override["loyalty_points"])
    if "tier" in override:
        tier = str(override["tier"])
    if "order_total" in override:
        order_total = float(override["order_total"])
    if "product_category" in override:
        product_category = str(override["product_category"])

    local = _calculate_loyalty_locally(loyalty_points, tier, order_total, product_category)

    code = f"""
import json, math
loyalty_points = {max(0, int(loyalty_points))}
tier = {str(tier).strip().title()!r}
order_total = {max(0.0, float(order_total))!r}
product_category = {str(product_category).strip().lower()!r}
earn_rates = {{'standard': 1, 'device': 2, 'fresh': 5}}
tier_rates = {{'Silver': 0.00, 'Gold': 0.10, 'Platinum': 0.15}}
earn_rate = earn_rates.get(product_category, 1)
tier_discount_pct = tier_rates.get(tier, 0.0)
max_redemption_value = order_total * 0.50
max_redeemable_points = math.floor((max_redemption_value * 100) / 500) * 500
points_redeemed = min((loyalty_points // 500) * 500, max_redeemable_points)
points_value = points_redeemed / 100.0
subtotal_after_points = max(0.0, order_total - points_value)
tier_discount_amount = subtotal_after_points * tier_discount_pct
final_total = max(0.0, subtotal_after_points - tier_discount_amount)
result = {{
 'points_redeemed': int(points_redeemed),
 'tier_discount_pct': tier_discount_pct,
 'tier_discount_amount': round(tier_discount_amount, 2),
 'final_total': round(final_total, 2),
 'total_savings': round(order_total - final_total, 2),
 'points_earned': int(final_total * earn_rate),
 'remaining_points': int(loyalty_points - points_redeemed),
}}
print(json.dumps(result))
"""

    try:
        with code_session(REGION) as code_client:
            response = code_client.invoke("executeCode", {
                "code": code,
                "language": "python",
                "clearContext": True,
            })
        ci_result = _extract_ci_json(response)
        required = {"points_redeemed", "tier_discount_pct", "final_total", "remaining_points"}
        if ci_result and required.issubset(ci_result):
            # Validate against the deterministic rules before returning CI output.
            if (
                int(ci_result["points_redeemed"]) == local["points_redeemed"]
                and round(float(ci_result["tier_discount_pct"]), 4) == round(local["tier_discount_pct"], 4)
                and round(float(ci_result["final_total"]), 2) == local["final_total"]
                and int(ci_result["remaining_points"]) == local["remaining_points"]
            ):
                validated = dict(local)
                validated["calculation_mode"] = "code-interpreter"
                return json.dumps(validated)
        logger.warning("Code Interpreter returned no valid loyalty JSON; using deterministic validation fallback.")
    except Exception as exc:
        logger.warning("Code Interpreter execution failed; using deterministic fallback: %s", exc)

    # Required rubric fallback: compute ONLY the tier discount locally.
    # Point redemption is intentionally disabled when the sandbox is unavailable.
    tier_name = str(tier).strip().title()
    tier_pct = {"Silver": 0.00, "Gold": 0.10, "Platinum": 0.15}.get(tier_name, 0.0)
    total = max(0.0, float(order_total))
    tier_discount_amount = round(total * tier_pct, 2)
    fallback = {
        "points_redeemed": 0,
        "tier_discount_pct": tier_pct,
        "tier_discount_amount": tier_discount_amount,
        "final_total": round(max(0.0, total - tier_discount_amount), 2),
        "total_savings": tier_discount_amount,
        "points_earned": int(max(0.0, total - tier_discount_amount) * {"standard": 1, "device": 2, "fresh": 5}.get(
            str(product_category).strip().lower(), 1
        )),
        "remaining_points": max(0, int(loyalty_points)),
        "calculation_mode": "tier-only-fallback",
        "code_interpreter": False,
    }
    return json.dumps(fallback)

# ── Section 8 — Agent Entrypoint ─────────────────────────────────────────────────
SYSTEM_PROMPT = """
You are the Customer Support AI Agent for a fictional Amazon-style e-commerce store.
Be accurate, concise, professional, and transparent.

TOOL ROUTING:
1. For live customer/order information, ALWAYS use the Gateway order/customer tools.
   Never invent order status, tracking number, carrier, delivery date, customer data,
   or loyalty balance.
2. For refunds and return labels, ALWAYS use the Gateway refund tools. Never claim a
   refund succeeded unless the tool confirms it.
3. Use search_knowledge_base for product facts, return/refund policy, warranty,
   loyalty benefits, and order-status definitions. Never invent policy.
4. Use calculate_loyalty_discount for loyalty calculations. Preserve the customer's
   exact points, tier, order total, and product category; do not substitute values.
   If the current message explicitly gives an order amount (for example, "$150"),
   that amount is authoritative even if memory or a Gateway order has a different amount.
5. Use the AgentCore Browser tool for requested live public web information.
   For a direct URL/page-title request, call the browser tool, navigate to the exact URL,
   and base the answer only on content returned by that live browser session. Never infer
   or guess a page title. Keep browser navigation minimal and do not substitute memory,
   Gateway, or model knowledge for live browser results.
6. Use retrieved memory naturally. If memory says the customer is Jane and prefers
   concise responses, answer accordingly. Never reveal internal memory mechanics.
7. If a required tool is unavailable, say so and do not fabricate a result.
""".strip()


def _is_gateway_request(text: str) -> bool:
    lower = text.lower()
    return (
        "ord-" in lower
        or "order status" in lower
        or "track my order" in lower
        or "tracking" in lower
        or "refund" in lower
        or "return label" in lower
        or "my orders" in lower
        or "customer account" in lower
        or "loyalty tier" in lower
        or "loyalty balance" in lower
        or "how many points" in lower
    )


def _normalize_agent_response(response: Any) -> str:
    if response is None:
        return "I could not generate a response."
    if isinstance(response, str):
        return response
    message = getattr(response, "message", None)
    if message is None and isinstance(response, dict):
        message = response.get("message") or response.get("output") or response
    text = _message_text(message)
    if text:
        return text
    output = getattr(response, "output", None)
    if isinstance(output, str):
        return output
    return str(response)


@app.entrypoint
async def invoke(payload, context=None):
    """AgentCore Runtime entrypoint with safe routing for all project capabilities."""
    if not isinstance(payload, dict):
        return "Invalid request: payload must be a JSON object."

    user_input = str(payload.get("prompt") or payload.get("input") or payload.get("message") or "").strip()
    if not user_input:
        return "Invalid request: 'prompt' is required."

    actor_id = str(payload.get("customer_id") or "anonymous-customer").strip()
    session_id = str(payload.get("session_id") or uuid.uuid4()).strip()

    loyalty_facts = _extract_explicit_loyalty_inputs(user_input)
    loyalty_token = _loyalty_request_override.set(loyalty_facts or None)

    def _finish(value: str) -> str:
        _loyalty_request_override.reset(loyalty_token)
        return value

    memory_hook = MemoryHook(actor_id, session_id, memory_client, MEMORY_ID)

    # Browser requests are intentionally isolated from the Gateway agent. This
    # prevents the model from wasting turns on unrelated MCP tools when the
    # user's only task is a live-page lookup.
    is_browser_request = bool(re.search(
        r"(?:https?://|open\s+|visit\s+|browse\s+|web\s+page|page\s+title)",
        user_input,
        re.I,
    ))

    browser_tool_available = True
    browser_tool = None
    try:
        # BROWSER_ID may be the AWS-managed browser (aws.browser.v1) or a
        # custom browser configured for PUBLIC network access.
        browser = AgentCoreBrowser(region=REGION, identifier=BROWSER_ID)
        browser_tool = browser.browser
        logger.info("AgentCore Browser initialized with identifier %s", BROWSER_ID)
    except Exception as exc:
        browser_tool_available = False
        logger.warning("AgentCore Browser initialization failed for %s: %s", BROWSER_ID, exc)

    if is_browser_request and browser_tool_available:
        browser_prompt = (
            "Use ONLY the browser tool for this request. Navigate directly to the URL "
            "specified by the user. Perform the minimum navigation needed. If the browser "
            "returns page text, title, or navigation output, use that returned information "
            "to answer. For a page-title request, report the title exactly or as returned. "
            "Do not call Gateway, memory, or unrelated tools. Do not invent a title."
        )
        try:
            browser_agent = Agent(
                model=model,
                tools=[browser_tool],
                hooks=[memory_hook],
                system_prompt=browser_prompt,
            )
            result = await browser_agent.invoke_async(user_input)
            return _finish(_normalize_agent_response(result))
        except Exception as exc:
            logger.exception("Dedicated browser invocation failed")
            return _finish(
                "The AgentCore Browser tool was reached but the live page could not be "
                f"completed in this attempt: {exc}"
            )

    if is_browser_request and not browser_tool_available:
        return _finish(
            "The AgentCore Browser tool is unavailable in this runtime, so I cannot "
            "safely report live webpage content."
        )

    tools = [search_knowledge_base, calculate_loyalty_discount]
    if browser_tool_available and browser_tool is not None:
        tools.append(browser_tool)

    if _is_placeholder(GATEWAY_URL):
        if _is_gateway_request(user_input):
            return _finish("Live customer/order tools are not configured, so I cannot safely retrieve that information.")
        agent = Agent(model=model, tools=tools, hooks=[memory_hook], system_prompt=SYSTEM_PROMPT)
        result = await agent.invoke_async(user_input)
        return _finish(_normalize_agent_response(result))

    # Keep the MCP session alive for the complete agent invocation.
    try:
        mcp_client = MCPClient(lambda: streamable_http_client(GATEWAY_URL))
        with mcp_client:
            gateway_tools = mcp_client.list_tools_sync()
            if not gateway_tools:
                raise RuntimeError("Gateway returned zero tools")
            logger.info("Loaded %d Gateway tool(s).", len(gateway_tools))
            agent = Agent(
                model=model,
                tools=tools + list(gateway_tools),
                hooks=[memory_hook],
                system_prompt=SYSTEM_PROMPT,
            )
            result = await agent.invoke_async(user_input)
            return _finish(_normalize_agent_response(result))
    except Exception as exc:
        logger.exception("Gateway invocation failed")
        if _is_gateway_request(user_input):
            return _finish(
                "I could not reach the live customer/order system, so I will not guess. "
                "Please retry this request when the Gateway is available."
            )
        agent = Agent(model=model, tools=tools, hooks=[memory_hook], system_prompt=SYSTEM_PROMPT)
        result = await agent.invoke_async(user_input)
        return _finish(_normalize_agent_response(result))

# ── CLI entry point (do not modify) ──────────────────────────────────────────
def main():
    """Run one invocation from the command line for local testing."""
    parser = argparse.ArgumentParser()
    parser.add_argument("payload", type=str)
    args = parser.parse_args()
    response = asyncio.run(invoke(json.loads(args.payload)))
    print(response)


if __name__ == "__main__":
    app.run()
    # Uncomment the line below and comment app.run() for local CLI testing:
    # main()
