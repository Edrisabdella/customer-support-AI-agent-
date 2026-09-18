# Rubric Traceability Matrix

| Rubric requirement | Implementation / evidence location |
|---|---|
| BedrockAgentCoreApp at module level | `agent/main.py` → `app = BedrockAgentCoreApp()` |
| Async `invoke` + `@app.entrypoint` | `agent/main.py` → `async def invoke(...)` |
| `app.run()` entry point | `agent/main.py` bottom block |
| Successful `agentcore invoke` | `submission/TEST_EVIDENCE.md` — capture actual output |
| Gateway MCP integration | `agent/main.py` → `MCPClient` + streamable HTTP transport |
| Two Gateway-backed tools | Real Gateway target design: `order-tracker` API target + `refund-processor` Lambda target |
| RAG `@tool` | `search_knowledge_base()` in `agent/main.py` |
| Bedrock Retrieve API | `_bedrock_runtime.retrieve(...)` in `agent/main.py` |
| KB no-result/config guard | `search_knowledge_base()` |
| `get_namespaces()` | `agent/main.py` |
| `MemoryHook(HookProvider)` | `agent/main.py` |
| Retrieve memories and inject context | `retrieve_customer_context()` |
| Persist interaction with `create_event()` | `save_support_interaction()` |
| Cross-session memory evidence | Test 4A + 4B in `submission/TEST_EVIDENCE.md` |
| Code Interpreter | `calculate_loyalty_discount()` with `code_session(...).invoke("executeCode", ...)` |
| Required structured loyalty fields | `points_redeemed`, `tier_discount_pct`, `final_total`, `remaining_points` plus savings/earnings |
| Code Interpreter fallback | deterministic tier-only fallback in same function |
| Browser | `AgentCoreBrowser(region=REGION)` and `browser.browser` in tools |
| Browser live-page evidence | Test 6 in `submission/TEST_EVIDENCE.md` |
| Reflection | `submission/reflection.md` (200–400 words) |
| CloudWatch | `submission/CLOUDWATCH.md` + actual alarm screenshot required |
| Architecture | `assets/aws_deployment_architecture_actual_resources.png` |
| Real AWS resources | `docs/AWS_RESOURCE_MANIFEST.md` |
| No secrets in source | `.env.example` contains identifiers only; credentials intentionally excluded |
