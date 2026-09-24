# RESUBMISSION EVIDENCE MAP

Use this exact organization so every rubric item is easy to locate.

```text
submission/
└── EVIDENCE SCREENSHOOT/
    ├── 01-runtime-ready.png
    ├── 02-gateway-api-and-lambda.png
    ├── 03-rag.png
    ├── 04-memory-session-a.png
    ├── 05-memory-session-b.png
    ├── 06-loyalty-code-interpreter.png
    └── 07-browser-live.png
```

| Rubric item | Source/code | Evidence |
|---|---|---|
| Runtime | `app/CustomerSupportAgent/main.py` | `01-runtime-ready.png` |
| MCP/Gateway | `MCPClient`, loaded Gateway tools | `02-gateway-api-and-lambda.png` |
| RAG | `search_knowledge_base()` + Bedrock Retrieve | `03-rag.png` |
| Memory | `MemoryHook`, namespace retrieval, `create_event()` | `04-memory-session-a.png`, `05-memory-session-b.png` |
| Code Interpreter | `calculate_loyalty_discount()` + `code_session().invoke("executeCode", ...)` | `06-loyalty-code-interpreter.png` |
| Browser | `AgentCoreBrowser(region=REGION, identifier=BROWSER_ID)` | `07-browser-live.png` |
| Reflection | `REFLECTION_200_400_WORDS.md` | included in submission root |
| Traceability | this file | included in submission root |

IMPORTANT:
- Evidence must be real captured output, not fabricated screenshots.
- Show the actual tool invocation/result where possible.
- Keep the filename/rubric mapping visible to the reviewer.
- Do not include AWS access keys, secret keys, session tokens, passwords, or private API keys.
