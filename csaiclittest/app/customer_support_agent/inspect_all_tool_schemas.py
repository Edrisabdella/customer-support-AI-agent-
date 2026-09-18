import asyncio
from mcp import ClientSession
from mcp_proxy_for_aws.client import aws_iam_streamablehttp_client

GATEWAY_URL = "https://customersupportgateway-uxvyatjhl6.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"

async def main():
    async with aws_iam_streamablehttp_client(
        GATEWAY_URL,
        "us-east-1",
    ) as (read_stream, write_stream, get_session_id):

        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tools = await session.list_tools()

            print("=" * 80)
            print("ALL GATEWAY TOOL DETAILS")
            print("=" * 80)

            for tool in tools.tools:
                print()
                print("NAME:")
                print(tool.name)

                print()
                print("DESCRIPTION:")
                print(tool.description)

                print()
                print("INPUT SCHEMA:")
                print(tool.inputSchema)

                print()
                print("-" * 80)

asyncio.run(main())
