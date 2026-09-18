import json
import uuid
from datetime import datetime, timedelta, timezone


# ============================================================
# RESPONSE HELPERS
# ============================================================

def success_response(data):
    return {
        "statusCode": 200,
        "body": json.dumps(data),
    }


def error_response(message, status_code=400):
    return {
        "statusCode": status_code,
        "body": json.dumps({
            "error": message
        }),
    }


# ============================================================
# AGENTCORE TOOL NAME
# ============================================================

def get_tool_name(context):
    """
    AgentCore Gateway provides the full tool name through
    context.client_context.custom.

    Example:
        refund-processor___check_refund_status

    We strip the target prefix and keep:
        check_refund_status
    """

    try:
        custom = context.client_context.custom or {}

        full_tool_name = custom.get(
            "bedrockAgentCoreToolName",
            ""
        )

        if "___" in full_tool_name:
            return full_tool_name.split("___", 1)[1]

        return full_tool_name

    except Exception:
        return ""


# ============================================================
# INITIATE REFUND
# ============================================================

def initiate_refund(event):

    order_id = event.get("order_id")
    reason = event.get("reason")
    amount = event.get("amount")

    if not order_id:
        return error_response(
            "order_id is required"
        )

    if not reason:
        return error_response(
            "reason is required"
        )

    refund_id = (
        "REF-" +
        str(uuid.uuid4()).replace("-", "")[:8].upper()
    )

    created_at = datetime.now(
        timezone.utc
    ).isoformat()

    if amount is None:
        amount = 0

    result = {
        "refund_id": refund_id,
        "order_id": str(order_id).upper(),
        "status": "APPROVED",
        "amount": float(amount),
        "reason": reason,
        "message": "Refund has been initiated successfully.",
        "created_at": created_at,
    }

    return success_response(result)


# ============================================================
# CHECK REFUND STATUS
# ============================================================

def check_refund_status(event):

    refund_id = event.get("refund_id")

    if not refund_id:
        return error_response(
            "refund_id is required"
        )

    result = {
        "refund_id": refund_id,
        "status": "PROCESSING",
        "eta": "2-3 business days",
    }

    return success_response(result)


# ============================================================
# GET RETURN LABEL
# ============================================================

def get_return_label(event):

    order_id = event.get("order_id")

    if not order_id:
        return error_response(
            "order_id is required"
        )

    order_id = str(order_id).upper()

    # Generate a return label validity date 30 days
    # from the time the label is requested.
    valid_until = (
        datetime.now(timezone.utc) +
        timedelta(days=30)
    ).date().isoformat()

    result = {
        "order_id": order_id,
        "label_url": (
            f"https://returns.amazon.com/label/{order_id}"
        ),
        "carrier": "UPS",
        "valid_until": valid_until,
    }

    return success_response(result)


# ============================================================
# MAIN LAMBDA HANDLER
# ============================================================

def lambda_handler(event, context):

    try:
        print("AgentCore Refund Lambda event:")
        print(json.dumps(event, default=str))

        tool_name = get_tool_name(context)

        print(f"AgentCore refund tool name: {tool_name}")

        # ----------------------------------------------------
        # CHECK REFUND STATUS
        # ----------------------------------------------------

        if tool_name == "check_refund_status":

            return check_refund_status(event)

        # ----------------------------------------------------
        # GET RETURN LABEL
        # ----------------------------------------------------

        elif tool_name == "get_return_label":

            return get_return_label(event)

        # ----------------------------------------------------
        # INITIATE REFUND
        # ----------------------------------------------------

        elif tool_name == "initiate_refund":

            return initiate_refund(event)

        # ----------------------------------------------------
        # UNKNOWN TOOL
        # ----------------------------------------------------

        return error_response(
            f"Unknown AgentCore refund tool: {tool_name}"
        )

    except Exception as exc:

        print(f"Unhandled Lambda error: {exc}")

        return error_response(
            f"Internal Lambda error: {str(exc)}",
            500
        )