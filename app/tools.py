"""Tools and callable functions exposed to the Gemini GenAI model."""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from app.db import ORDERS_DB, DELIVERY_POLICIES, ESCALATION_TICKETS, REPORTED_ISSUES


def get_order_status(order_id: str) -> Dict[str, Any]:
    """Retrieve detailed real-time status, ETA, and courier location for an order.
    
    Args:
        order_id: The order ID to look up (e.g., ORD-1001, ORD-1002, ORD-1003, ORD-1004).
    """
    clean_id = order_id.strip().upper()
    order = ORDERS_DB.get(clean_id)
    if not order:
        return {
            "success": False,
            "error": f"Order with ID '{order_id}' was not found. Please verify the order number."
        }
    
    return {
        "success": True,
        "order_id": order["order_id"],
        "status": order["status_display"],
        "restaurant": order["restaurant_name"],
        "items": order["items"],
        "total_amount": f"${order['total_amount']:.2f}",
        "delivery_address": order["delivery_address"],
        "delivery_notes": order.get("delivery_notes", "None"),
        "courier": order.get("courier"),
        "eta_minutes": order.get("eta_minutes"),
        "delivered_at": order.get("delivered_at")
    }


def update_delivery_address(
    order_id: str, 
    new_address: Optional[str] = None, 
    delivery_notes: Optional[str] = None
) -> Dict[str, Any]:
    """Update delivery address or driver drop-off notes for an active order.
    
    Args:
        order_id: The order ID (e.g., ORD-1003).
        new_address: The new physical destination address (only permitted if order is still 'preparing').
        delivery_notes: Special delivery instructions (e.g. 'Leave on porch', gate codes, call upon arrival).
    """
    clean_id = order_id.strip().upper()
    order = ORDERS_DB.get(clean_id)
    if not order:
        return {"success": False, "error": f"Order '{order_id}' not found."}
    
    status = order.get("status")
    
    if status == "delivered":
        return {
            "success": False,
            "error": "This order has already been delivered. The address cannot be changed."
        }
    
    if new_address and status in ["out_for_delivery", "delayed"]:
        # Policy: Address cannot be changed once courier is dispatched, but instructions can be
        if delivery_notes:
            order["delivery_notes"] = delivery_notes
            return {
                "success": False,
                "partial_update": True,
                "message": (
                    "Your order is already on its way with the driver, so the physical address cannot be changed. "
                    f"However, we successfully updated your delivery notes to: '{delivery_notes}'."
                )
            }
        return {
            "success": False,
            "error": (
                "The order is already with the courier on delivery route. We cannot alter the delivery address "
                "mid-route, but you can provide special drop-off instructions or gate codes."
            )
        }
    
    # Update permitted
    if new_address:
        order["delivery_address"] = new_address
    if delivery_notes:
        order["delivery_notes"] = delivery_notes
        
    return {
        "success": True,
        "order_id": clean_id,
        "updated_address": order["delivery_address"],
        "updated_notes": order.get("delivery_notes"),
        "message": "Delivery details updated successfully."
    }


def report_delivery_issue(
    order_id: str, 
    issue_type: str, 
    details: str, 
    affected_items: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Report a problem with an order, such as damaged food, missing items, late arrival, or wrong order.
    
    Args:
        order_id: The order ID.
        issue_type: Category of issue ('missing_item', 'damaged_item', 'wrong_order', 'late_delivery', 'cold_food').
        details: Specific customer description of the problem.
        affected_items: List of item names that were damaged, missing, or incorrect.
    """
    clean_id = order_id.strip().upper()
    order = ORDERS_DB.get(clean_id)
    if not order:
        return {"success": False, "error": f"Order '{order_id}' not found."}
    
    report_id = f"RPT-{uuid.uuid4().hex[:6].upper()}"
    report_entry = {
        "report_id": report_id,
        "order_id": clean_id,
        "issue_type": issue_type,
        "details": details,
        "affected_items": affected_items or [],
        "timestamp": datetime.utcnow().isoformat(),
        "status": "investigating"
    }
    REPORTED_ISSUES.append(report_entry)
    
    return {
        "success": True,
        "report_id": report_id,
        "order_id": clean_id,
        "issue_type": issue_type,
        "status": "Logged and verified",
        "message": f"Issue report {report_id} has been registered for {order['restaurant_name']}."
    }


def process_refund_or_credit(
    order_id: str, 
    reason: str, 
    amount: Optional[float] = None,
    refund_method: str = "delivery_wallet"
) -> Dict[str, Any]:
    """Process an automated instant refund or wallet credit for verified order complaints.
    
    Args:
        order_id: The order ID to issue refund/credit for.
        reason: Explanation for the compensation (e.g. 'Missing Truffle Fries', 'Over 30 mins late').
        amount: Specific amount in USD to refund. If not provided, calculates appropriate compensation.
        refund_method: Either 'delivery_wallet' (instant) or 'original_payment_method' (3-5 business days).
    """
    clean_id = order_id.strip().upper()
    order = ORDERS_DB.get(clean_id)
    if not order:
        return {"success": False, "error": f"Order '{order_id}' not found."}
        
    if order.get("refund_issued"):
        return {
            "success": False,
            "error": "A refund has already been previously issued for this order."
        }
        
    final_amount = amount if amount is not None else min(order.get("total_amount", 10.0), 20.0)
    
    # Check limit for automated chatbot approvals
    if final_amount > 50.0:
        return {
            "success": False,
            "requires_human_approval": True,
            "amount": final_amount,
            "message": "Refund amounts over $50.00 require review by a human supervisor."
        }
        
    order["refund_issued"] = True
    transaction_id = f"TXN-REF-{uuid.uuid4().hex[:6].upper()}"
    
    return {
        "success": True,
        "transaction_id": transaction_id,
        "order_id": clean_id,
        "refund_amount": f"${final_amount:.2f}",
        "refund_method": "Instant Delivery Wallet Credit" if refund_method == "delivery_wallet" else "Original Payment Card (3-5 business days)",
        "status": "Completed",
        "message": f"Successfully processed ${final_amount:.2f} to customer {refund_method}."
    }


def escalate_to_human_agent(
    order_id: str, 
    summary: str, 
    customer_sentiment: str = "frustrated"
) -> Dict[str, Any]:
    """Escalate the conversation to a live human support specialist when customer is unsatisfied or problem is complex.
    
    Args:
        order_id: Relevant order ID or 'GENERAL'.
        summary: Concise summary of the customer's problem and why human help is needed.
        customer_sentiment: Customer emotional state ('frustrated', 'angry', 'confused', 'urgent').
    """
    ticket_id = f"ESC-{uuid.uuid4().hex[:6].upper()}"
    ticket = {
        "ticket_id": ticket_id,
        "order_id": order_id.strip().upper(),
        "summary": summary,
        "customer_sentiment": customer_sentiment,
        "timestamp": datetime.utcnow().isoformat(),
        "queue_position": len(ESCALATION_TICKETS) + 1,
        "status": "assigned_to_human"
    }
    ESCALATION_TICKETS.append(ticket)
    
    return {
        "success": True,
        "ticket_id": ticket_id,
        "queue_position": ticket["queue_position"],
        "estimated_wait_seconds": 60,
        "agent_name": "Jordan P. (Tier 2 Delivery Specialist)",
        "message": f"Human agent assigned (Ticket #{ticket_id}). Jordan P. will take over within 1 minute."
    }


def get_delivery_policy(topic: str) -> Dict[str, Any]:
    """Retrieve official company delivery policies and rules.
    
    Args:
        topic: The policy area to check ('cancellation', 'refund_and_replacement', 'address_change', 'delivery_delay', 'operating_hours').
    """
    clean_topic = topic.strip().lower()
    policy = DELIVERY_POLICIES.get(clean_topic)
    
    if not policy:
        available_topics = list(DELIVERY_POLICIES.keys())
        return {
            "success": False,
            "error": f"Topic '{topic}' not found. Available topics: {', '.join(available_topics)}"
        }
        
    return {
        "success": True,
        "topic": clean_topic,
        "policy": policy
    }


# Map tool names to actual Python functions for dispatcher
AVAILABLE_TOOLS = {
    "get_order_status": get_order_status,
    "update_delivery_address": update_delivery_address,
    "report_delivery_issue": report_delivery_issue,
    "process_refund_or_credit": process_refund_or_credit,
    "escalate_to_human_agent": escalate_to_human_agent,
    "get_delivery_policy": get_delivery_policy
}
