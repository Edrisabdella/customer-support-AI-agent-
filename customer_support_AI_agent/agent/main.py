"""
Customer Support AI Agent
=========================
Amazon Bedrock AgentCore + Strands SDK implementation.

Rubric mapping (section headers match the project rubric):
  §1  BedrockAgentCoreApp instance + @app.entrypoint + app.run()
  §2  MCPClient Gateway integration (order-tracker API target + refund Lambda target)
  §3  search_knowledge_base  -> Bedrock Knowledge Base Retrieve API
  §4  MemoryHook + get_namespaces + retrieve_customer_context + save_support_interaction
  §5  calculate_loyalty_discount -> Code Interpreter with tier-only fallback
  §6  AgentCoreBrowser -> live web page retrieval
"""

from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.memory import MemoryClient
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamable_http_client
from strands.hooks import (
    HookProvider, AfterInvocationEvent, HookRegistry, MessageAddedEvent,
)
from bedrock_agentcore.tools.code_interpreter_client import code_session
from bedrock_agentcore.tools.browser_client import browser_session

import argparse
import asyncio
import json
import logging
import os
import re
import uuid
from contextvars import ContextVar
from typing import Any, Dict, Optional

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("CSAI_Agent")

# ═══════════════════════════════════════════════════════════════════════════════
# §1  App Initialisation + Configuration
# ═══════════════════════════════════════════════════════════════════════════════
app = BedrockAgentCoreApp()
os.environ["BYPASS_TOOL_CONSENT"] = "true"

GATEWAY_URL = os.getenv(
    "GATEWAY_URL",
    "https://customersupportgateway-uxvyatjhl6.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp",
).strip()
KB_ID     = os.getenv("KB_ID", "W6RC69EXD5").strip()
REGION    = os.getenv("AWS_REGION", "us-east-1").strip() or "us-east-1"
MEMORY_ID = os.getenv("MEMORY_ID", "CustomerSupportMemory-ECNYSn3F91").strip()
BROWSER_ID = os.getenv("BROWSER_ID", "aws.browser.v1").strip() or "aws.browser.v1"

model_id = "global.amazon.nova-2-lite-v1:0"
model = BedrockModel(model_id=model_id)
memory_client = MemoryClient(region_name=REGION)

import boto3
_bedrock_runtime = boto3.client("bedrock-agent-runtime", region_name=REGION)

# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════
def _is_placeholder(v: str) -> bool:
    return not v or v.startswith("<") or v.endswith(">")


def _extract_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if isinstance(value.get("text"), str):
            return value["text"]
        for k in ("content", "output", "message", "value"):
            if k in value:
                t = _extract_text(value[k])
                if t:
                    return t
        return ""
    if isinstance(value, list):
        return "".join(_extract_text(i) for i in value if i)
    return str(value)


def _message_text(msg: Any) -> str:
    return _extract_text(msg.get("content")) if isinstance(msg, dict) else ""


def _message_role(msg: Any) -> str:
    return str(msg.get("role", "")).lower() if isinstance(msg, dict) else ""


def _normalize_agent_response(response: Any) -> str:
    if response is None:
        return "I could not generate a response."
    if isinstance(response, str):
        return response
    msg = getattr(response, "message", None)
    if msg is None and isinstance(response, dict):
        msg = response.get("message") or response.get("output") or response
    t = _message_text(msg)
    if t:
        return t
    out = getattr(response, "output", None)
    return out if isinstance(out, str) else str(response)


# ═══════════════════════════════════════════════════════════════════════════════
# §4  Memory: namespaces + MemoryHook
# ═══════════════════════════════════════════════════════════════════════════════
def get_namespaces(mem_client: MemoryClient, memory_id: str) -> Dict[str, str]:
    """Return {strategy_type: namespace_template} from AgentCore Memory."""
    if _is_placeholder(memory_id):
        return {}
    resp = mem_client.get_memory_strategies(memory_id)
    strategies = resp.get("strategies", []) if isinstance(resp, dict) else resp
    out: Dict[str, str] = {}
    for s in strategies or []:
        if not isinstance(s, dict):
            continue
        stype = s.get("type") or s.get("strategyType") or s.get("name")
        templates = s.get("namespaces") or s.get("namespaceTemplates") or []
        if stype and templates:
            out[str(stype)] = str(templates[0])
    return out


class MemoryHook(HookProvider):
    """Retrieves long-term customer context and persists each completed turn."""

    def __init__(self, actor_id, session_id, memory_client, memory_id):
        self.actor_id = actor_id
        self.session_id = session_id
        self.memory_client = memory_client
        self.memory_id = memory_id
        self.namespaces = get_namespaces(memory_client, memory_id)
        self.original_user_query = ""
        self.last_assistant_response = ""

    @staticmethod
    def _fmt(template: str, actor_id: str) -> str:
        return (template.replace("{actorId}", actor_id)
                        .replace("{actor_id}", actor_id))

    def _records(self, response: Any) -> list:
        if isinstance(response, dict):
            for k in ("memoryRecords", "memories", "results", "records"):
                v = response.get(k)
                if isinstance(v, list):
                    return v
        return response if isinstance(response, list) else []

    def _rec_text(self, record: Any) -> str:
        if isinstance(record, str):
            return record.strip()
        if not isinstance(record, dict):
            return ""
        for k in ("content", "text", "memory", "record", "value"):
            if k in record:
                t = _extract_text(record[k]).strip()
                if t:
                    return t
        return ""

    # Rubric: retrieve_customer_context
    def retrieve_customer_context(self, event: MessageAddedEvent):
        if _is_placeholder(self.memory_id):
            return
        message = getattr(event, "message", None)
        if not isinstance(message, dict) or _message_role(message) != "user":
            return
        query = _message_text(message).strip()
        if not query or query.startswith("Customer Context:\n"):
            return
        self.original_user_query = query

        memories: list[str] = []
        for stype, template in self.namespaces.items():
            ns = self._fmt(template, self.actor_id)
            try:
                resp = self.memory_client.retrieve_memories(
                    self.memory_id, namespace=ns, query=query, top_k=5,
                )
                for r in self._records(resp):
                    t = self._rec_text(r)
                    if t:
                        memories.append(f"[{stype}] {t}")
            except Exception as exc:
                logger.warning("Memory retrieval failed for %s: %s", stype, exc)

        if memories:
            enriched = f"Customer Context:\n{chr(10).join(memories)}\n\n{query}"
            message["content"] = [{"text": enriched}]

    def _find_turn(self, messages: Any) -> tuple[str, str]:
        u, a = self.original_user_query, self.last_assistant_response
        for m in reversed(messages or []):
            role = _message_role(m)
            text = _message_text(m).strip()
            if not text:
                continue
            if role == "assistant" and not a:
                a = text
            elif role == "user" and not u:
                u = text
            if u and a:
                break
        return u, a

    # Rubric: save_support_interaction -> memory_client.create_event()
    def save_support_interaction(self, event: AfterInvocationEvent):
        if _is_placeholder(self.memory_id):
            return
        messages = getattr(event.agent, "messages", [])
        user_text, assistant_text = self._find_turn(messages)
        if not user_text or not assistant_text:
            logger.warning("Memory save skipped — missing user/assistant text.")
            return
        try:
            self.memory_client.create_event(
                memory_id=self.memory_id,
                actor_id=self.actor_id,
                session_id=self.session_id,
                messages=[(user_text, "USER"), (assistant_text, "ASSISTANT")],
            )
            logger.info("Saved support interaction for actor %s", self.actor_id)
        except Exception as exc:
            logger.warning("Memory save failed: %s", exc)

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(MessageAddedEvent, self.retrieve_customer_context)
        registry.add_callback(AfterInvocationEvent, self.save_support_interaction)


# ═══════════════════════════════════════════════════════════════════════════════
# §3  Knowledge Base RAG tool
# ═══════════════════════════════════════════════════════════════════════════════
@tool
def search_knowledge_base(query: str) -> str:
    """
    Search the Amazon product catalog and support knowledge base.
    Use this for product specifications, return policies, warranty information,
    loyalty program details, and order-status definitions. Do NOT use it for
    live order lookup; use the Gateway order tools for that.

    Args:
        query: The question or topic to search for.

    Returns:
        Relevant information retrieved from the knowledge base.
    """
    if _is_placeholder(KB_ID):
        return "Knowledge base not configured. Set KB_ID before using RAG."
    try:
        resp = _bedrock_runtime.retrieve(
            knowledgeBaseId=KB_ID,
            retrievalQuery={"text": query},
        )
        results = resp.get("retrievalResults", [])
        if not results:
            return "No relevant knowledge-base results were found."
        chunks = []
        for r in results:
            content = r.get("content", {}) if isinstance(r, dict) else {}
            t = _extract_text(content).strip()
            if t:
                chunks.append(t)
        return "\n---\n".join(chunks) if chunks else "No relevant KB text found."
    except Exception as exc:
        logger.exception("KB retrieval failed")
        return f"Knowledge base retrieval failed: {exc}"


# ═══════════════════════════════════════════════════════════════════════════════
# §5  Loyalty discount — Code Interpreter + tier-only fallback
# ═══════════════════════════════════════════════════════════════════════════════
_loyalty_override: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "loyalty_override", default=None,
)


def _extract_explicit_loyalty_inputs(text: str) -> Dict[str, Any]:
    """Explicit values in the current request are authoritative over memory."""
    facts: Dict[str, Any] = {}
    lower = text.lower()

    pts = re.findall(r"\b([0-9][0-9,]*)\s*(?:loyalty\s*)?points\b", text, re.I)
    if pts:
        facts["loyalty_points"] = int(pts[-1].replace(",", ""))

    for tier in ("Platinum", "Gold", "Silver"):
        if re.search(rf"\b{tier}\b", text, re.I):
            facts["tier"] = tier
            break

    money = re.findall(r"\$\s*([0-9]+(?:\.[0-9]{1,2})?)", text)
    if money:
        facts["order_total"] = float(money[-1])
    else:
        prose = re.findall(
            r"(?:order\s+(?:total|amount)|place\s+(?:a|an)?\s*\$?\s*order)"
            r".{0,60}?\b([0-9]+(?:\.[0-9]{1,2})?)\s*(?:dollars?|usd)\b",
            text, re.I,
        )
        if prose:
            facts["order_total"] = float(prose[-1])

    if re.search(r"\bstandard(?:[- ]shipping)?\b", lower):
        facts["product_category"] = "standard"
    elif re.search(r"\b(?:device|amazon\s+device)\b", lower):
        facts["product_category"] = "device"
    elif re.search(r"\bfresh\b", lower):
        facts["product_category"] = "fresh"

    return facts


def _calc_locally(points: int, tier: str, total: float, cat: str) -> Dict[str, Any]:
    points = max(0, int(points))
    total = max(0.0, float(total))
    tier = str(tier).strip().title()
    cat = str(cat).strip().lower()

    earn_rates = {"standard": 1, "device": 2, "fresh": 5}
    tier_rates = {"Silver": 0.00, "Gold": 0.10, "Platinum": 0.15}

    earn_rate = earn_rates.get(cat, 1)
    tier_pct = tier_rates.get(tier, 0.0)

    max_value = total * 0.50
    max_points = int(max_value * 100) // 500 * 500
    redeemed = min((points // 500) * 500, max_points)
    points_value = redeemed / 100.0
    subtotal = max(0.0, total - points_value)
    tier_amt = subtotal * tier_pct
    final = max(0.0, subtotal - tier_amt)
    savings = max(0.0, total - final)
    earned = int(final * earn_rate)
    remaining = points - redeemed

    return {
        "points_redeemed": int(redeemed),
        "tier_discount_pct": tier_pct,
        "tier_discount_amount": round(tier_amt, 2),
        "final_total": round(final, 2),
        "total_savings": round(savings, 2),
        "points_earned": earned,
        "remaining_points": int(remaining),
    }


def _extract_ci_stdout(response: Any) -> Optional[Dict[str, Any]]:
    """Extract JSON from AgentCore Code Interpreter stream response."""
    if not isinstance(response, dict):
        return None
    for event in response.get("stream", []):
        if not isinstance(event, dict):
            continue
        result = event.get("result") or {}
        if not isinstance(result, dict):
            continue

        # Shape 1: result.content[].text  (official)
        content = result.get("content")
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    try:
                        parsed = json.loads(item["text"].strip())
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        pass

        # Shape 2: result.structuredContent.stdout
        structured = result.get("structuredContent") or {}
        if isinstance(structured, dict) and isinstance(structured.get("stdout"), str):
            try:
                parsed = json.loads(structured["stdout"].strip())
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

        # Shape 3: result.text
        if isinstance(result.get("text"), str):
            try:
                parsed = json.loads(result["text"].strip())
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass
    return None


@tool
def calculate_loyalty_discount(
    loyalty_points: int,
    tier: str,
    order_total: float,
    product_category: str = "standard",
) -> str:
    """
    Calculate loyalty points redemption and tier discount using the AgentCore
    Code Interpreter sandbox.

    Rules: standard/device/fresh earn 1/2/5 points per dollar;
    Silver/Gold/Platinum receive 0%/10%/15% tier discounts;
    100 points = $1; redemption is in 500-point blocks with a 500-point
    minimum and is capped at 50% of the order value. Tier discount applies
    AFTER points redemption.

    Returns JSON with: points_redeemed, tier_discount_pct, tier_discount_amount,
    final_total, total_savings, points_earned, remaining_points.
    """
    ov = _loyalty_override.get() or {}
    if "loyalty_points" in ov: loyalty_points = int(ov["loyalty_points"])
    if "tier" in ov:           tier = str(ov["tier"])
    if "order_total" in ov:    order_total = float(ov["order_total"])
    if "product_category" in ov: product_category = str(ov["product_category"])

    # Local deterministic version for validation
    local = _calc_locally(loyalty_points, tier, order_total, product_category)

    # Code string executed in the sandbox
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

    # ── Try the Code Interpreter sandbox ──────────────────────────────────────
    try:
        with code_session(REGION) as code_client:
            response = code_client.invoke("executeCode", {
                "code": code,
                "language": "python",
                "clearContext": True,
            })
        ci = _extract_ci_stdout(response)
        required = {"points_redeemed", "tier_discount_pct", "final_total", "remaining_points"}
        if ci and required.issubset(ci):
            # Sanity check against local arithmetic
            if (int(ci["points_redeemed"]) == local["points_redeemed"]
                and round(float(ci["tier_discount_pct"]), 4) == round(local["tier_discount_pct"], 4)
                and round(float(ci["final_total"]), 2) == local["final_total"]
                and int(ci["remaining_points"]) == local["remaining_points"]):
                out = dict(local)
                out["calculation_mode"] = "code-interpreter"
                return json.dumps(out)
        logger.warning("Code Interpreter returned no valid loyalty JSON; using fallback.")
    except Exception as exc:
        logger.warning("Code Interpreter unavailable, using fallback: %s", exc)

    # ── RUBRIC-REQUIRED FALLBACK: tier-only discount ──────────────────────────
    # When the sandbox is unavailable we compute ONLY the tier discount.
    # Points are NOT redeemed, and no points are earned.
    tier_name = str(tier).strip().title()
    tier_pct = {"Silver": 0.00, "Gold": 0.10, "Platinum": 0.15}.get(tier_name, 0.0)
    total = max(0.0, float(order_total))
    tier_amt = round(total * tier_pct, 2)
    fallback = {
        "points_redeemed": 0,
        "tier_discount_pct": tier_pct,
        "tier_discount_amount": tier_amt,
        "final_total": round(max(0.0, total - tier_amt), 2),
        "total_savings": tier_amt,
        "points_earned": 0,
        "remaining_points": max(0, int(loyalty_points)),
        "calculation_mode": "tier-only-fallback",
        "code_interpreter": False,
    }
    return json.dumps(fallback)


# ═══════════════════════════════════════════════════════════════════════════════
# §6  Browser tool — live web page retrieval
# ═══════════════════════════════════════════════════════════════════════════════
@tool
def browse_web_page(url: str) -> str:
    """
    Browse a live public web page and return its title and visible text.

    Use this whenever the customer asks you to open, visit, or browse a URL,
    or asks for the current title/content of a live page. Do NOT invent page
    titles — always call this tool and report the value it returns.

    Args:
        url: The fully qualified URL to open (must start with http:// or https://).

    Returns:
        JSON string with keys: url, title, content (truncated), error (if any).
    """
    if not url.startswith(("http://", "https://")):
        return json.dumps({"url": url, "error": "URL must start with http:// or https://"})

    try:
        with browser_session(REGION, identifier=BROWSER_ID) as client:
            ws_url, headers = client.generate_ws_headers()

            # Playwright's sync API can't run inside an already-running event
            # loop. Use the async API and drive it via asyncio.run_coroutine_threadsafe
            # if we're inside a loop, or a fresh loop if we're not.
            from playwright.async_api import async_playwright

            async def _fetch() -> dict:
                async with async_playwright() as pw:
                    browser = await pw.chromium.connect_over_cdp(
                        ws_url, headers=headers,
                    )
                    ctx = await browser.new_context()
                    page = await ctx.new_page()
                    try:
                        await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                        title = await page.title()
                        # Give the page a moment to render dynamic content
                        await page.wait_for_timeout(1500)
                        body = await page.evaluate(
                            "() => document.body ? document.body.innerText : ''"
                        )
                    finally:
                        try:
                            await ctx.close()
                        except Exception:
                            pass
                        try:
                            await browser.close()
                        except Exception:
                            pass
                    return {
                        "url": page.url,
                        "title": title or "(no title)",
                        "content": (body or "")[:4000],
                    }

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # Called from within an async context — run on a worker thread.
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    result = pool.submit(lambda: asyncio.run(_fetch())).result(timeout=90)
            else:
                result = asyncio.run(_fetch())

            return json.dumps(result)
    except Exception as exc:
        logger.exception("Browser tool failed")
        return json.dumps({
            "url": url,
            "error": f"Browser navigation failed: {exc}",
        })


# ═══════════════════════════════════════════════════════════════════════════════
# §2  Agent entrypoint — Gateway + all tools
# ═══════════════════════════════════════════════════════════════════════════════
SYSTEM_PROMPT = """
You are the Customer Support AI Agent for a fictional Amazon-style e-commerce store.
Be accurate, concise, professional, and transparent.

TOOL ROUTING:
1. For live customer/order information, ALWAYS use the Gateway order/customer tools.
   Never invent order status, tracking numbers, carriers, or delivery dates.
2. For refunds and return labels, ALWAYS use the Gateway refund tools. Never claim
   a refund succeeded unless the tool confirms it.
3. Use search_knowledge_base for product facts, return/refund policy, warranty,
   loyalty benefits, and order-status definitions. Never invent policy.
4. Use calculate_loyalty_discount for loyalty calculations. Preserve the customer's
   exact points, tier, order total, and product category. If the current message
   gives an explicit order amount (e.g. "$150"), that amount is authoritative even
   if memory or a Gateway order has a different amount.
5. Use the browse_web_page tool whenever the customer asks you to open, visit, or
   browse a URL, or asks for the live title/content of a web page. Report only the
   title/content returned by the tool — never guess.
6. Use retrieved memory naturally. Never reveal internal memory mechanics.
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


@app.entrypoint
async def invoke(payload, context=None):
    """AgentCore Runtime entrypoint."""
    if not isinstance(payload, dict):
        return "Invalid request: payload must be a JSON object."

    user_input = str(
        payload.get("prompt") or payload.get("input") or payload.get("message") or ""
    ).strip()
    if not user_input:
        return "Invalid request: 'prompt' is required."

    actor_id   = str(payload.get("customer_id") or "anonymous-customer").strip()
    session_id = str(payload.get("session_id") or uuid.uuid4()).strip()

    # Capture explicit loyalty inputs for the current turn
    facts = _extract_explicit_loyalty_inputs(user_input)
    token = _loyalty_override.set(facts or None)

    def _finish(value: str) -> str:
        _loyalty_override.reset(token)
        return value

    memory_hook = MemoryHook(actor_id, session_id, memory_client, MEMORY_ID)

    # Base tool set is always available
    tools = [search_knowledge_base, calculate_loyalty_discount, browse_web_page]

    if _is_placeholder(GATEWAY_URL):
        if _is_gateway_request(user_input):
            return _finish(
                "Live customer/order tools are not configured, so I cannot "
                "safely retrieve that information."
            )
        agent = Agent(model=model, tools=tools, hooks=[memory_hook],
                      system_prompt=SYSTEM_PROMPT)
        result = await agent.invoke_async(user_input)
        return _finish(_normalize_agent_response(result))

    # ── Attach Gateway tools via MCPClient (§2 rubric) ────────────────────────
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
                "I could not reach the live customer/order system, so I will not "
                "guess. Please retry this request when the Gateway is available."
            )
        agent = Agent(model=model, tools=tools, hooks=[memory_hook],
                      system_prompt=SYSTEM_PROMPT)
        result = await agent.invoke_async(user_input)
        return _finish(_normalize_agent_response(result))


# ── CLI entry point ──────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("payload", type=str)
    args = parser.parse_args()
    response = asyncio.run(invoke(json.loads(args.payload)))
    print(response)


if __name__ == "__main__":
    app.run()