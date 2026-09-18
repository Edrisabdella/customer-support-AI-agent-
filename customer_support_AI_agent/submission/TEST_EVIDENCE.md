# Six Rubric Tests — Exact Commands and Evidence Plan

**Important:** These are the rubric tests and expected behaviors. The package does not fabricate successful outputs. Run them against the deployed Runtime and save the actual terminal results/screenshots.

## Test 1 — Order Tracking

```powershell
agentcore invoke '{"prompt":"Can you track order ORD-001?","customer_id":"CUST-123","session_id":"t1"}'
```

Expected evidence: a successful response containing `SHIPPED`, tracking number `TRK987654321`, carrier `UPS`, and an estimated delivery date.

Save as: `submission/evidence/01_order_tracking.png` or `.txt`.

## Test 2 — Refund Processing

```powershell
agentcore invoke '{"prompt":"I want to return my Kindle Paperwhite (ORD-002). Please initiate a refund.","customer_id":"CUST-123","session_id":"t2"}'
```

Expected evidence: a refund ID, `APPROVED`, and a `3-5 business days` message.

Save as: `02_refund_processing.png` or `.txt`.

## Test 3 — Knowledge Base / RAG

```powershell
agentcore invoke '{"prompt":"What are the benefits of the Platinum loyalty tier?","customer_id":"CUST-123","session_id":"t3"}'
```

Expected evidence: free same-day shipping, 15% discount, and priority customer support, grounded in the Knowledge Base.

Save as: `03_knowledge_base_rag.png` or `.txt`.

Also capture the `CustomerSupportKB` configuration/status screen.

## Test 4A — Memory Session A

```powershell
agentcore invoke '{"prompt":"Hi, I am Jane. I prefer concise responses.","customer_id":"CUST-123","session_id":"s-A"}'
```

Wait at least 30 seconds for memory extraction, as specified by the project document.

Save as: `04A_memory_session_A.png` or `.txt`.

## Test 4B — Memory Session B

```powershell
agentcore invoke '{"prompt":"Do you remember my name and communication preference?","customer_id":"CUST-123","session_id":"s-B"}'
```

Expected evidence: the agent recalls `Jane` and the preference for concise responses, while using a different session ID and the same customer ID.

Save as: `04B_memory_session_B.png` or `.txt`.

## Test 5 — Loyalty Discount / Code Interpreter

```powershell
agentcore invoke '{"prompt":"I am a Gold member with 4250 points. Calculate my discount on a $150 standard order.","customer_id":"CUST-123","session_id":"t5"}'
```

Expected calculation under the project rules:

- Starting points: 4250
- Redeem: 4000 points
- Point value: $40
- Remaining subtotal: $110
- Gold tier discount: 10% = $11
- Total savings: $51
- Final total: $99
- Remaining points: 250

Save as: `05_loyalty_discount.png` or `.txt`.

## Test 6 — Browser Tool

```powershell
agentcore invoke '{"prompt":"Go to https://www.amazon.com and tell me the page title.","customer_id":"CUST-123","session_id":"t6"}'
```

Expected evidence: the title returned from the live Amazon.com page. Do not replace the live title with a hard-coded expected string.

Save as: `06_browser.png` or `.txt`.

## Evidence quality rules

- Keep the command and response visible in each capture.
- Do not include credentials, API keys, access tokens, or private secrets.
- Do not create screenshots from expected text; use actual AWS/Runtime output.
- For Test 4, both sessions are required to prove cross-session memory.
- For the Gateway rubric, make sure the logs visibly show successful use of both an API-backed tool and a Lambda-backed tool.
