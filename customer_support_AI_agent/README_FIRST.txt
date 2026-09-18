AWS Future Engineers — Project 2 Customer Support AI Agent

1. Back up your current main.py:
   Copy-Item main.py main.py.backup-before-100pct -Force

2. Replace main.py with the supplied main.py.

3. Run:
   uv run python -m py_compile main.py
   uv run python -c "import main; print('MAIN IMPORT: OK')"
   uv run python verify_project2.py

4. Required functional tests:
   uv run python local_test.py "Where is my order ORD-001?" --customer-id CUST-123
   uv run python local_test.py "Please process a refund for order ORD-002." --customer-id CUST-123
   uv run python local_test.py "I am a Platinum customer. What benefits do I receive?" --customer-id CUST-123
   uv run python local_test.py "I am a Gold customer with 4250 loyalty points. I want to place a $150 standard-shipping order. Calculate my final total after redeeming points and applying my Gold discount. Do not use any existing order amount; use exactly $150 as the order total." --customer-id CUST-123
   uv run python local_test.py "Open https://www.amazon.com and tell me the page title."
   uv run python local_test.py "Hi, I am Jane. I prefer concise responses." --customer-id CUST-123
   # Wait 90–120 seconds for AgentCore Memory extraction, then:
   uv run python local_test.py "What is my name, and what response style do I prefer?" --customer-id CUST-123

5. Deploy only after local tests pass:
   uv run agentcore configure --entrypoint main.py --name customer_support_agent
   uv run agentcore deploy --local-build

6. Invoke deployed agent using the exact project scenarios and capture terminal output/screenshots for submission.

Important: keep AWS credentials out of source code and do not paste credential values into submissions.
