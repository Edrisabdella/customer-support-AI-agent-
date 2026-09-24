# FINAL RESUBMISSION CHECKLIST

## A. Code changes required by reviewer

- [x] Loyalty calculation executes the calculation inside AgentCore Code Interpreter.
- [x] If Code Interpreter is unavailable, fallback is **tier-only**; it does not redeem points.
- [x] Loyalty output remains structured with:
  - `points_redeemed`
  - `tier_discount_pct`
  - `final_total`
  - `remaining_points`
- [x] Browser uses an explicit configurable `BROWSER_ID`.
- [x] Browser can use a dedicated custom Browser configured with `PUBLIC` network access.
- [x] Browser requests are isolated and instructed to use live browser results only.
- [x] Container runtime configuration is retained for Browser compatibility.

## B. Local checks

From:

```text
C:\Users\user\Desktop\A AWS FUTURE ENGINEERS\PROJECT2\CustomerSupportDeploy
```

Run:

```powershell
cd ".\app\CustomerSupportAgent"
uv sync
uv run python -m py_compile .\main.py
cd "..\.."
agentcore validate
```

Do not submit if `agentcore validate` fails.

## C. Browser resource

Create/configure the browser and verify:

```powershell
aws bedrock-agentcore-control get-browser `
  --region us-east-1 `
  --browser-id "<BROWSER_ID>"
```

Status must be `READY`.

## D. Deploy

Because the Browser-enabled runtime should use Container:

```powershell
agentcore deploy --yes --env BROWSER_ID="<BROWSER_ID>"
```

Then:

```powershell
agentcore status
```

Confirm the runtime is READY.

## E. Required six tests

Capture real outputs for:

1. Order tracking
2. Refund
3. RAG
4. Memory across two sessions
5. Loyalty calculation showing Code Interpreter
6. Browser live web retrieval

## F. CloudWatch

Verify the required ERROR metric filter and alarm before submission.

The alarm should be:

```text
Metric: CustomerSupportAgentErrors
Statistic: Sum
Period: 5 minutes
Evaluation periods: 1
Condition: GreaterThanThreshold
Threshold: 5
```

Capture the alarm screenshot and include it in the evidence folder if the submission instructions require it.

## G. Final package

Do not submit old failed evidence alongside the new evidence.

The final submission should make the mapping obvious:

```text
01 = Runtime
02 = Gateway
03 = RAG
04-05 = Memory
06 = Code Interpreter loyalty
07 = Browser
```
