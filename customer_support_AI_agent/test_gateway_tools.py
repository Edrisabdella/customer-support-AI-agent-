import asyncio
import json

from mcp import ClientSession
from mcp_proxy_for_aws.client import aws_iam_streamablehttp_client


GATEWAY_URL = (
    "https://customersupportgateway-uxvyatjhl6"
    ".gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"
)

REGION = "us-east-1"


async def call_tool(session, tool_name, arguments):
    print()
    print("=" * 70)
    print(f"CALLING: {tool_name}")
    print("=" * 70)

    print("Arguments:")
    print(json.dumps(arguments, indent=2))

    try:
        result = await session.call_tool(
            tool_name,
            arguments,
        )

        print()
        print("RESULT:")
        print("-" * 70)

        print(result)

        print()
        print("Structured result:")
        if getattr(result, "structuredContent", None):
            print(
                json.dumps(
                    result.structuredContent,
                    indent=2,
                    default=str,
                )
            )

        return result

    except Exception as e:
        print()
        print("ERROR:")
        print(type(e).__name__)
        print(str(e))

        return None


async def main():

    print("=" * 70)
    print("AGENTCORE GATEWAY TOOL EXECUTION TEST")
    print("=" * 70)

    print()
    print("Gateway:")
    print(GATEWAY_URL)

    async with aws_iam_streamablehttp_client(
        endpoint=GATEWAY_URL,
        aws_region=REGION,
        aws_service="bedrock-agentcore",
    ) as (
        read_stream,
        write_stream,
        get_session_id,
    ):

        print()
        print("✓ Transport created")

        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:

            print("✓ Initializing MCP session...")

            await session.initialize()

            print("✓ MCP session initialized")

            # ----------------------------------------------------------
            # 1. LIST TOOLS
            # ----------------------------------------------------------

            tools = await session.list_tools()

            print()
            print(f"✓ Gateway exposes {len(tools.tools)} tools")

            # ----------------------------------------------------------
            # 2. TEST ORDER TRACKER
            # ----------------------------------------------------------

            await call_tool(
                session,
                "customer-support-order-tracker-api___get_customer",
                {
                    "customer_id": "CUST-123"
                },
            )

            await call_tool(
                session,
                "customer-support-order-tracker-api___get_customer_orders",
                {
                    "customer_id": "CUST-123"
                },
            )

            await call_tool(
                session,
                "customer-support-order-tracker-api___get_order",
                {
                    "order_id": "ORD-001"
                },
            )

            # ----------------------------------------------------------
            # 3. TEST KNOWLEDGE BASE
            # ----------------------------------------------------------

            await call_tool(
                session,
                "kb-target-vy1vuf___Retrieve",
                {
                    "retrievalQuery": {
                        "text": "What is the refund policy?"
                    }
                },
            )

            # ----------------------------------------------------------
            # 4. TEST REFUND STATUS
            # ----------------------------------------------------------

            await call_tool(
                session,
                "refund-processor___check_refund_status",
                {
                    "refund_id": "REF-001"
                },
            )

            # ----------------------------------------------------------
            # 5. TEST RETURN LABEL
            # ----------------------------------------------------------

            await call_tool(
                session,
                "refund-processor___get_return_label",
                {
                    "order_id": "ORD-001"
                },
            )

            # ----------------------------------------------------------
            # 6. DO NOT INITIATE A REAL REFUND YET
            # ----------------------------------------------------------

            print()
            print("=" * 70)
            print("REFUND INITIATION")
            print("=" * 70)
            print()
            print(
                "SKIPPED intentionally."
            )
            print(
                "We will test initiate_refund only after verifying"
            )
            print(
                "the complete agent flow."
            )

    print()
    print("=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())