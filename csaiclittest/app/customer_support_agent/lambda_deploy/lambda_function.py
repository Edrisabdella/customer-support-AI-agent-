import json
from datetime import datetime, timedelta, timezone


# -------------------------------------------------------------------
# MOCK CUSTOMER DATA
# -------------------------------------------------------------------

CUSTOMERS = {
    "CUST-123": {
        "customer_id": "CUST-123",
        "name": "Jane Smith",
        "loyalty_points": 4250,
        "loyalty_tier": "Gold",
    },
    "CUST-456": {
        "customer_id": "CUST-456",
        "name": "Bob Johnson",
        "loyalty_points": 890,
        "loyalty_tier": "Silver",
    },
}


# -------------------------------------------------------------------
# MOCK ORDER DATA
# -------------------------------------------------------------------

NOW = datetime.now(timezone.utc)

ORDERS = {
    "ORD-001": {
        "order_id": "ORD-001",
        "customer_id": "CUST-123",
        "status": "SHIPPED",
        "items": [
            {
                "product_id": "PROD-001",
                "product_name": "Wireless Headphones Pro",
                "quantity": 1,
                "price": 89.99,
            }
        ],
        "total": 89.99,
        "tracking_number": "TRK987654321",
        "carrier": "UPS",
        "estimated_delivery": (
            NOW + timedelta(days=2)
        ).date().isoformat(),
    },
    "ORD-002": {
        "order_id": "ORD-002",
        "customer_id": "CUST-123",
        "status": "DELIVERED",
        "items": [
            {
                "product_id": "PROD-002",
                "product_name": "Kindle Paperwhite",
                "quantity": 1,
                "price": 139.99,
            }
        ],
        "total": 139.99,
        "tracking_number": "TRK123456789",
        "carrier": "USPS",
        "delivered_date": (
            NOW - timedelta(days=3)
        ).date().isoformat(),
    },
    "ORD-003": {
        "order_id": "ORD-003",
        "customer_id": "CUST-456",
        "status": "PROCESSING",
        "items": [
            {
                "product_id": "PROD-003",
                "product_name": "Echo Dot 5th Gen",
                "quantity": 2,
                "price": 49.99,
            },
            {
                "product_id": "PROD-004",
                "product_name": "Smart Plug",
                "quantity": 1,
                "price": 24.99,
            },
        ],
        "total": 124.97,
        "estimated_delivery": (
            NOW + timedelta(days=5)
        ).date().isoformat(),
    },
}


# -------------------------------------------------------------------
# RESPONSE HELPER
# -------------------------------------------------------------------

def response(status_code, body):
    return {
        "statusCode": status_code,
        "body": json.dumps(body),
    }


# -------------------------------------------------------------------
# TOOL FUNCTIONS
# -------------------------------------------------------------------

def get_customer(customer_id):
    customer_id = customer_id.upper()

    customer = CUSTOMERS.get(customer_id)

    if not customer:
        return response(
            404,
            {
                "error": "Customer not found",
                "customer_id": customer_id,
            },
        )

    return response(200, customer)


def get_customer_orders(customer_id):
    customer_id = customer_id.upper()

    if customer_id not in CUSTOMERS:
        return response(
            404,
            {
                "error": "Customer not found",
                "customer_id": customer_id,
            },
        )

    customer_orders = [
        order
        for order in ORDERS.values()
        if order["customer_id"] == customer_id
    ]

    return response(
        200,
        {
            "customer_id": customer_id,
            "orders": customer_orders,
            "count": len(customer_orders),
        },
    )


def get_order(order_id):
    order_id = order_id.upper()

    order = ORDERS.get(order_id)

    if not order:
        return response(
            404,
            {
                "error": "Order not found",
                "order_id": order_id,
            },
        )

    return response(200, order)


# -------------------------------------------------------------------
# LAMBDA HANDLER
# -------------------------------------------------------------------

def lambda_handler(event, context):

    print("===== ORDER TRACKER EVENT =====")
    print(json.dumps(event, default=str))

    print("===== ORDER TRACKER CONTEXT =====")
    print(str(context))

    # ---------------------------------------------------------------
    # Determine the request type.
    #
    # API Gateway AWS_PROXY calls provide:
    #   resource
    #   httpMethod
    #   pathParameters
    #
    # AgentCore Gateway Lambda targets provide:
    #   bedrockAgentCoreToolName
    # in context.client_context.custom
    # ---------------------------------------------------------------

    tool_name = ""

    try:
        if (
            context
            and context.client_context
            and context.client_context.custom
        ):
            tool_name = context.client_context.custom.get(
                "bedrockAgentCoreToolName",
                "",
            )
    except Exception as exc:
        print(f"Could not read AgentCore tool name: {exc}")

    # AgentCore format:
    # target-name___tool-name
    if "___" in tool_name:
        tool_name = tool_name.split("___", 1)[1]

    # ---------------------------------------------------------------
    # If this is an API Gateway request, determine the tool from
    # the resource path.
    # ---------------------------------------------------------------

    resource = event.get("resource", "")
    http_method = event.get("httpMethod", "")
    path_parameters = event.get("pathParameters") or {}

    if not tool_name and http_method == "GET":

        if resource == "/customers/{customer_id}":
            tool_name = "get_customer"

        elif resource == "/customers/{customer_id}/orders":
            tool_name = "get_customer_orders"

        elif resource == "/orders/{order_id}":
            tool_name = "get_order"

    print(f"===== RESOLVED TOOL: {tool_name} =====")

    # ---------------------------------------------------------------
    # Tool: get_customer
    # ---------------------------------------------------------------

    if tool_name == "get_customer":

        customer_id = event.get("customer_id")

        if not customer_id:
            customer_id = path_parameters.get("customer_id")

        if not customer_id:
            return response(
                400,
                {
                    "error": "Missing required parameter: customer_id"
                },
            )

        return get_customer(customer_id)

    # ---------------------------------------------------------------
    # Tool: get_customer_orders
    # ---------------------------------------------------------------

    if tool_name == "get_customer_orders":

        customer_id = event.get("customer_id")

        if not customer_id:
            customer_id = path_parameters.get("customer_id")

        if not customer_id:
            return response(
                400,
                {
                    "error": "Missing required parameter: customer_id"
                },
            )

        return get_customer_orders(customer_id)

    # ---------------------------------------------------------------
    # Tool: get_order
    # ---------------------------------------------------------------

    if tool_name == "get_order":

        order_id = event.get("order_id")

        if not order_id:
            order_id = path_parameters.get("order_id")

        if not order_id:
            return response(
                400,
                {
                    "error": "Missing required parameter: order_id"
                },
            )

        return get_order(order_id)

    # ---------------------------------------------------------------
    # Unknown request
    # ---------------------------------------------------------------

    return response(
        400,
        {
            "error": "Unknown order tracker request",
            "tool_name": tool_name,
            "resource": resource,
            "httpMethod": http_method,
        },
    )
