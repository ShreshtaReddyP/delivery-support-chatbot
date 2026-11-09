"""In-memory mock database for Delivery Support Chatbot."""

from datetime import datetime
from typing import Dict, Any, Optional

ORDERS_DB: Dict[str, Dict[str, Any]] = {
    "ORD-1001": {
        "order_id": "ORD-1001",
        "customer_id": "CUST-8801",
        "customer_name": "Jordan Smith",
        "restaurant_name": "Mario's Artisan Pizza",
        "status": "out_for_delivery",
        "status_display": "Out for Delivery",
        "items": [
            {"name": "Pepperoni Pizza (Large)", "qty": 1, "price": 22.00},
            {"name": "Garlic Knots (6 pcs)", "qty": 1, "price": 7.50},
            {"name": "Diet Coke (500ml)", "qty": 2, "price": 5.00}
        ],
        "total_amount": 34.50,
        "delivery_address": "742 Evergreen Terrace, Springfield, OR",
        "delivery_notes": "Ring doorbell twice, leave on porch.",
        "courier": {
            "name": "Alex Rivera",
            "vehicle": "Silver Honda Civic",
            "phone": "+1-555-0192",
            "current_location": "2 blocks away on Oak Street",
            "rating": 4.9
        },
        "eta_minutes": 10,
        "created_at": "35 mins ago",
        "refund_issued": False
    },
    "ORD-1002": {
        "order_id": "ORD-1002",
        "customer_id": "CUST-8801",
        "customer_name": "Jordan Smith",
        "restaurant_name": "Urban Burger Co.",
        "status": "delivered",
        "status_display": "Delivered",
        "items": [
            {"name": "Double Smash Burger", "qty": 2, "price": 24.00},
            {"name": "Truffle Parmesan Fries", "qty": 1, "price": 8.00},
            {"name": "Chocolate Milkshake", "qty": 1, "price": 6.50}
        ],
        "total_amount": 38.50,
        "delivery_address": "742 Evergreen Terrace, Springfield, OR",
        "delivery_notes": "Leave at front desk.",
        "courier": {
            "name": "David Kim",
            "vehicle": "E-Bike",
            "phone": "+1-555-0144",
            "rating": 4.8
        },
        "delivered_at": "25 minutes ago",
        "refund_issued": False
    },
    "ORD-1003": {
        "order_id": "ORD-1003",
        "customer_id": "CUST-8801",
        "customer_name": "Jordan Smith",
        "restaurant_name": "Sakura Japanese Kitchen",
        "status": "preparing",
        "status_display": "Kitchen is Preparing Order",
        "items": [
            {"name": "Salmon Avocado Roll (8 pcs)", "qty": 2, "price": 22.00},
            {"name": "Spicy Tuna Roll (8 pcs)", "qty": 1, "price": 12.00},
            {"name": "Miso Soup", "qty": 2, "price": 6.00}
        ],
        "total_amount": 40.00,
        "delivery_address": "742 Evergreen Terrace, Springfield, OR",
        "delivery_notes": "",
        "courier": None,
        "eta_minutes": 35,
        "created_at": "10 mins ago",
        "refund_issued": False
    },
    "ORD-1004": {
        "order_id": "ORD-1004",
        "customer_id": "CUST-8801",
        "customer_name": "Jordan Smith",
        "restaurant_name": "Taco Fiesta",
        "status": "delayed",
        "status_display": "Delayed in Transit (Heavy Rain)",
        "items": [
            {"name": "Carne Asada Burrito", "qty": 2, "price": 18.00},
            {"name": "Chips & Guacamole", "qty": 1, "price": 7.00}
        ],
        "total_amount": 25.00,
        "delivery_address": "742 Evergreen Terrace, Springfield, OR",
        "delivery_notes": "Leave near front gate.",
        "courier": {
            "name": "Elena Rostova",
            "vehicle": "Toyota Prius",
            "phone": "+1-555-0188",
            "current_location": "Encountered detour on Main St due to weather",
            "rating": 4.95
        },
        "eta_minutes": 25,
        "original_eta_minutes": 10,
        "compensation_voucher_sent": False
    }
}

DELIVERY_POLICIES = {
    "cancellation": (
        "Orders can be canceled free of charge before the restaurant begins preparation. "
        "Once preparation starts, a 50% cancellation fee applies to cover food waste. "
        "Orders already out for delivery cannot be canceled."
    ),
    "refund_and_replacement": (
        "If items are missing, cold, spoiled, or damaged, customers are eligible for a replacement or a full "
        "refund of the affected items to their Delivery Wallet instantly, or back to the original card within 3-5 days. "
        "For claims exceeding $50, an escalation to human support is required for photo review."
    ),
    "address_change": (
        "Delivery address can be changed without charge while the order status is 'preparing'. "
        "If the order is already 'out for delivery', the address cannot be changed to a new distant neighborhood, "
        "but drop-off instructions or building gate codes can be updated immediately."
    ),
    "delivery_delay": (
        "If a delivery is delayed by more than 20 minutes past the original ETA, customers receive an automatic $5 "
        "in-app compensation credit coupon for their next order."
    ),
    "operating_hours": (
        "Customer support automated assistance is available 24/7. "
        "Human escalation agents are active daily from 7:00 AM to 1:00 AM local time."
    )
}

ESCALATION_TICKETS: list[Dict[str, Any]] = []
REPORTED_ISSUES: list[Dict[str, Any]] = []
