import asyncio

from mcp import ClientSession
from mcp_proxy_for_aws.client import aws_iam_streamablehttp_client


GATEWAY_URL = "https://customersupportgateway-uxvyatjhl6.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"


async def main():
    print("=" * 70)
    print("AGENTCORE GATEWAY REAL TOOL EXECUTION TEST")
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
        print("✓ Initializing MCP session...")

        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:

            await session.initialize()

            print("✓ MCP session initialized")
            print()
            print("Calling get_order...")
            print("-" * 70)

            result = await session.call_tool(
                "customer-support-order-tracker-api___get_order",
                {
                    "order_id": "ORD-001"
                },
            )

            print()
            print("RAW RESULT:")
            print(result)

            print()
            print("CONTENT:")

            for item in result.content:
                print(item)

            print()
            print("STRUCTURED CONTENT:")

            if hasattr(result, "structuredContent"):
                print(result.structuredContent)

            print()
            print("=" * 70)
            print("TEST COMPLETE")
            print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
