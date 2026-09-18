import asyncio
import json

from mcp import ClientSession
from mcp_proxy_for_aws.client import aws_iam_streamablehttp_client

GATEWAY_URL = (
    "https://customersupportgateway-uxvyatjhl6.gateway."
    "bedrock-agentcore.us-east-1.amazonaws.com/mcp"
)


def print_result(tool_name, result):
    print()
    print("=" * 70)
    print(f"RESULT: {tool_name}")
    print("=" * 70)
    print(f"isError: {result.isError}")

    for item in result.content:
        print(f"CONTENT: {item}")

        if hasattr(item, "text"):
            try:
                data = json.loads(item.text)
                print("PARSED JSON:")
                print(json.dumps(data, indent=2))
            except Exception:
                pass

    print()


async def main():

    print("=" * 70)
    print("AGENTCORE GATEWAY - ALL 8 TOOLS TEST")
    print("=" * 70)

    async with aws_iam_streamablehttp_client(
        GATEWAY_URL,
        "us-east-1",
    ) as (
        read_stream,
        write_stream,
        get_session_id,
    ):

        print("✓ Transport created")

        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:

            await session.initialize()

            print("✓ MCP session initialized")
            print()

            # ----------------------------------------------------------
            # 1. GET CUSTOMER
            # ----------------------------------------------------------
            print("[1/8] Testing get_customer...")

            result = await session.call_tool(
                "customer-support-order-tracker-api___get_customer",
                {
                    "customer_id": "CUST-123"
                },
            )

            print_result(
                "get_customer",
                result,
            )

            # ----------------------------------------------------------
            # 2. GET CUSTOMER ORDERS
            # ----------------------------------------------------------
            print("[2/8] Testing get_customer_orders...")

            result = await session.call_tool(
                "customer-support-order-tracker-api___get_customer_orders",
                {
                    "customer_id": "CUST-123"
                },
            )

            print_result(
                "get_customer_orders",
                result,
            )

            # ----------------------------------------------------------
            # 3. GET ORDER
            # ----------------------------------------------------------
            print("[3/8] Testing get_order...")

            result = await session.call_tool(
                "customer-support-order-tracker-api___get_order",
                {
                    "order_id": "ORD-001"
                },
            )

            print_result(
                "get_order",
                result,
            )

            # ----------------------------------------------------------
            # 4. KB AGENTIC RETRIEVE STREAM
            # ----------------------------------------------------------
            print("[4/8] Testing AgenticRetrieveStream...")

            result = await session.call_tool(
                "kb-target-vy1vuf___AgenticRetrieveStream",
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": {
                                "text": "What can you tell me about customer support?"
                            },
                        }
                    ]
                },
            )

            print_result(
                "AgenticRetrieveStream",
                result,
            )

            # ----------------------------------------------------------
            # 5. KB RETRIEVE
            # ----------------------------------------------------------
            print("[5/8] Testing Retrieve...")

            result = await session.call_tool(
                "kb-target-vy1vuf___Retrieve",
                {
                    "retrievalQuery": {
                        "text": "customer support policies"
                    }
                },
            )

            print_result(
                "Retrieve",
                result,
            )

            # ----------------------------------------------------------
            # 6. CHECK REFUND STATUS
            # ----------------------------------------------------------
            print("[6/8] Testing check_refund_status...")

            result = await session.call_tool(
                "refund-processor___check_refund_status",
                {
                    "refund_id": "REF-001"
                },
            )

            print_result(
                "check_refund_status",
                result,
            )

            # ----------------------------------------------------------
            # 7. GET RETURN LABEL
            # ----------------------------------------------------------
            print("[7/8] Testing get_return_label...")

            result = await session.call_tool(
                "refund-processor___get_return_label",
                {
                    "order_id": "ORD-001"
                },
            )

            print_result(
                "get_return_label",
                result,
            )

            # ----------------------------------------------------------
            # 8. INITIATE REFUND
            # ----------------------------------------------------------
            print("[8/8] Testing initiate_refund...")

            result = await session.call_tool(
                "refund-processor___initiate_refund",
                {
                    "order_id": "ORD-001",
                    "reason": "Customer changed their mind",
                    "amount": 89.99,
                },
            )

            print_result(
                "initiate_refund",
                result,
            )

    print()
    print("=" * 70)
    print("ALL 8 TOOL TESTS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())