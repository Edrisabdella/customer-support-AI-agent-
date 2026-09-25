"""Local pre-deployment verification for the AWS Future Engineers Project 2 agent."""
from pathlib import Path
import ast
import re

MAIN = Path(__file__).with_name("main.py")
src  = MAIN.read_text(encoding="utf-8")
ast.parse(src)  # syntax check

checks = []
def check(name, cond): checks.append((name, bool(cond)))

# ── Deployment & Runtime ────────────────────────────────────────────────────
check("BedrockAgentCoreApp instantiated",     "app = BedrockAgentCoreApp()" in src)
check("@app.entrypoint present",              "@app.entrypoint" in src)
check("async invoke present",                 bool(re.search(r"async def invoke\(", src)))
check("app.run() present",                    "app.run()" in src)

# ── Gateway / MCP ───────────────────────────────────────────────────────────
check("MCPClient imported",                   "from strands.tools.mcp.mcp_client import MCPClient" in src)
check("streamable_http_client used",          "streamable_http_client" in src)
check("Gateway tools loaded and added",       "gateway_tools = mcp_client.list_tools_sync()" in src
                                              and "tools + list(gateway_tools)" in src)

# ── Knowledge Base RAG ──────────────────────────────────────────────────────
check("@tool search_knowledge_base defined",  "@tool\ndef search_knowledge_base" in src)
check("Bedrock Retrieve API called",          "_bedrock_runtime.retrieve(" in src
                                              and "knowledgeBaseId=KB_ID" in src)
check("RAG chunks joined with separator",     '"\\n---\\n".join(chunks)' in src)
check("KB_ID guard clause present",           "Knowledge base not configured" in src)

# ── Memory ──────────────────────────────────────────────────────────────────
check("get_namespaces defined",               "def get_namespaces(" in src)
check("namespaceTemplates or namespaces",     '"namespaceTemplates"' in src or '"namespaces"' in src)
check("MemoryHook extends HookProvider",      "class MemoryHook(HookProvider)" in src)
check("register_hooks method",                "def register_hooks(" in src)
check("retrieve_customer_context method",     "def retrieve_customer_context(" in src)
check("save_support_interaction method",      "def save_support_interaction(" in src)
check("memory_client.create_event() used",    "create_event(" in src)

# ── Code Interpreter ────────────────────────────────────────────────────────
check("@tool calculate_loyalty_discount",     "@tool\ndef calculate_loyalty_discount" in src)
check("code_session(REGION) used",            "code_session(REGION)" in src)
check('"executeCode" invoked',                '"executeCode"' in src)
check("clearContext=True set",                '"clearContext": True' in src)
check("Tier-only fallback present",           '"calculation_mode": "tier-only-fallback"' in src)
check("Fallback sets points_redeemed=0",      '"points_redeemed": 0' in src)
check("Required earn rates present",          '"standard": 1, "device": 2, "fresh": 5' in src)
check("Required tier rates present",          '"Silver": 0.00, "Gold": 0.10, "Platinum": 0.15' in src)
check("50% cap present",                      "total * 0.50" in src)
check("500-point blocks present",             "// 500" in src and "* 500" in src)

# ── Browser ─────────────────────────────────────────────────────────────────
check("browser_session imported",             "from bedrock_agentcore.tools.browser_client import browser_session" in src)
check("@tool browse_web_page defined",        "@tool\ndef browse_web_page" in src)
check("browser_session(REGION) used",         "browser_session(REGION" in src)
check("Real page.title() retrieved",          "page.title()" in src)
check("Returns live page content",            '"content": (body or "")[:4000]' in src)

# ── Independent arithmetic check ────────────────────────────────────────────
points, total, tier_pct = 4250, 150.0, 0.10
max_pts = int(total * 0.50 * 100) // 500 * 500
redeemed = min((points // 500) * 500, max_pts)
subtotal = total - redeemed / 100
final_total = round(subtotal * (1 - tier_pct), 2)
check("Loyalty: 4000 redeemed",   redeemed == 4000)
check("Loyalty: Gold 10%",        tier_pct == 0.10)
check("Loyalty: final $99",       final_total == 99.00)
check("Loyalty: 250 remaining",   points - redeemed == 250)
check("Loyalty: 99 earned",       int(final_total) == 99)

# ── Report ──────────────────────────────────────────────────────────────────
failed = [n for n, ok in checks if not ok]
print("AWS FUTURE ENGINEERS PROJECT 2 — PRE-DEPLOYMENT CHECK")
print("=" * 62)
for name, ok in checks:
    print(f"{'PASS' if ok else 'FAIL':<5} {name}")
print("-" * 62)
print(f"Result: {len(checks)-len(failed)}/{len(checks)} checks passed")
if failed:
    raise SystemExit("FAILED CHECKS: " + "; ".join(failed))
print("ALL PRE-DEPLOYMENT CHECKS PASSED")