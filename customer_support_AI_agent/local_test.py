import argparse
import asyncio
import uuid

from main import invoke


def main():
    parser = argparse.ArgumentParser(
        description="Local test runner for the Customer Support AI Agent"
    )
    parser.add_argument("prompt", help="Customer message to send to the agent")
    parser.add_argument(
        "--customer-id",
        default="CUST-123",
        help="Customer ID (default: CUST-123)",
    )
    parser.add_argument(
        "--session-id",
        default=None,
        help="Session ID (default: a new UUID)",
    )
    args = parser.parse_args()

    payload = {
        "prompt": args.prompt,
        "customer_id": args.customer_id,
        "session_id": args.session_id or str(uuid.uuid4()),
    }

    response = asyncio.run(invoke(payload))
    print(response)


if __name__ == "__main__":
    main()
