import asyncio
import json

from mcp import ClientSession
from mcp_proxy_for_aws.client import aws_iam_streamablehttp_client


GATEWAY_URL = (
    "https://customersupportgateway-uxvyatjhl6"
    ".gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"
)

REGION = "us-east-1"


async def main():
    print("=" * 70)
    print("AGENTCORE GATEWAY TOOL SCHEMA TEST")
    print("=" * 70)
    print()
    print("Gateway:")
    print(GATEWAY_URL)
    print()

    async with aws_iam_streamablehttp_client(
        endpoint=GATEWAY_URL,
        aws_region=REGION,
        aws_service="bedrock-agentcore",
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

            print("✓ Initializing MCP session...")
            await session.initialize()

            print("✓ MCP session initialized")
            print()

            result = await session.list_tools()

            print("=" * 70)
            print(f"FOUND {len(result.tools)} TOOLS")
            print("=" * 70)
            print()

            for index, tool in enumerate(result.tools, start=1):
                print(f"[{index}] {tool.name}")
                print("-" * 70)

                if tool.description:
                    print("Description:")
                    print(tool.description)
                    print()

                print("Input schema:")

                if getattr(tool, "inputSchema", None):
                    print(
                        json.dumps(
                            tool.inputSchema,
                            indent=2,
                            default=str,
                        )
                    )
                else:
                    print("No input schema returned.")

                print()
                print("=" * 70)
                print()

            print("✓ Gateway tool schema discovery completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())