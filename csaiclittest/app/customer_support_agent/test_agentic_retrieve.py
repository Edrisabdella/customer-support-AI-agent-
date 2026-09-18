import asyncio
import json

from mcp import ClientSession
from mcp_proxy_for_aws.client import aws_iam_streamablehttp_client


GATEWAY_URL = "https://customersupportgateway-uxvyatjhl6.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"

TOOL_NAME = "kb-target-vy1vuf___AgenticRetrieveStream"


async def main():
    print("=" * 80)
    print("AGENTIC RETRIEVE STREAM - DIRECT EXECUTION TEST")
    print("=" * 80)

    async with aws_iam_streamablehttp_client(
        GATEWAY_URL,
        "us-east-1",
    ) as (read_stream, write_stream, get_session_id):

        print("✓ Transport created")

        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:

            await session.initialize()

            print("✓ MCP session initialized")
            print()

            messages = [
                {
                    "role": "user",
                    "content": {
                        "text": "What is the return policy for Wireless Headphones Pro?"
                    },
                }
            ]

            print("Calling:")
            print(TOOL_NAME)
            print()
            print("INPUT:")
            print(json.dumps(messages, indent=2))
            print()
            print("-" * 80)

            try:
                result = await session.call_tool(
                    TOOL_NAME,
                    {
                        "messages": messages
                    },
                )

                print()
                print("RAW RESULT:")
                print(result)
                print()

                print("isError:", result.isError)
                print()

                print("CONTENT:")
                for item in result.content:
                    print(item)

                print()
                print("=" * 80)
                print("TEST COMPLETE")
                print("=" * 80)

            except Exception as e:
                print()
                print("=" * 80)
                print("EXCEPTION")
                print("=" * 80)
                print(type(e).__name__)
                print(str(e))
                print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
