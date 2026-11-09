"""Gemini Agent orchestrator with native function calling."""

import os
import json
import logging
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv

from app.models import Message, ToolExecutionDetail
from app.tools import (
    AVAILABLE_TOOLS,
    get_order_status,
    update_delivery_address,
    report_delivery_issue,
    process_refund_or_credit,
    escalate_to_human_agent,
    get_delivery_policy,
)

load_dotenv(override=True)
logger = logging.getLogger("delivery_support_chatbot")

SYSTEM_INSTRUCTION = """
You are "SwiftDrop Assistant", an intelligent, empathetic, and efficient customer support agent for a fast-paced food and package delivery service.

Your goals:
1. Provide accurate, real-time tracking information, driver details, and ETAs.
2. Resolve delivery issues (missing items, damaged food, delayed delivery, wrong address) using your available tools.
3. Follow company delivery policies fairly and transparently.
4. Keep answers concise, clear, and action-oriented. Avoid overly lengthy paragraphs.

Important Guidelines:
- TOOL CALLING: You MUST call relevant tools to fetch information or perform actions. Never fabricate courier locations, ETAs, or refund confirmations.
  * Use `get_order_status` when user asks about an order (e.g. ORD-1001, ORD-1002, ORD-1003, ORD-1004).
  * If the user doesn't mention an order ID, ask for it politely.
  * Use `update_delivery_address` to update address (only if preparing) or special drop-off instructions/gate codes.
  * Use `report_delivery_issue` when an item is missing, damaged, late, or cold.
  * Use `process_refund_or_credit` when refund or wallet compensation is warranted per policy.
  * Use `get_delivery_policy` if the user questions cancellation, refund, or delay policies.
  * Use `escalate_to_human_agent` if the user is excessively frustrated, asks for a human, or if a refund exceeds chatbot limits ($50).
- Empathy: Acknowledge customer frustration warmly if their food is late or damaged before offering a resolution.
"""

TOOL_FUNCTIONS = [
    get_order_status,
    update_delivery_address,
    report_delivery_issue,
    process_refund_or_credit,
    escalate_to_human_agent,
    get_delivery_policy
]


class DeliverySupportAgent:
    def __init__(self):
        load_dotenv(override=True)
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initialize Google GenAI client if API key is provided."""
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            logger.warning("No valid GEMINI_API_KEY detected. Agent running in smart mock fallback mode.")
            return

        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
            logger.info("Successfully initialized google-genai Client with model: %s", self.model_name)
        except Exception as e:
            logger.warning("Failed to initialize google-genai client (%s). Trying legacy google.generativeai...", e)
            try:
                import google.generativeai as legacy_genai
                legacy_genai.configure(api_key=self.api_key)
                self.legacy_model = legacy_genai.GenerativeModel(
                    model_name=self.model_name,
                    tools=TOOL_FUNCTIONS,
                    system_instruction=SYSTEM_INSTRUCTION
                )
                logger.info("Successfully initialized legacy google.generativeai model.")
            except Exception as ex2:
                logger.error("Could not initialize Gemini client: %s", ex2)

    def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute one of the registered local tools and return the result."""
        tool_fn = AVAILABLE_TOOLS.get(tool_name)
        if not tool_fn:
            return {"error": f"Tool '{tool_name}' not implemented."}
        try:
            return tool_fn(**args)
        except Exception as e:
            logger.exception("Error executing tool %s with args %s: %s", tool_name, args, e)
            return {"error": str(e)}

    def run_chat(self, user_message: str, history: List[Message]) -> Tuple[str, List[ToolExecutionDetail]]:
        """Process user message using Gemini with native function calling, falling back to mock if no API key."""
        tool_executions: List[ToolExecutionDetail] = []

        # If live Gemini client is ready, use it
        if self.client:
            try:
                from google.genai import types
                
                # Format conversation history
                contents = []
                for msg in history:
                    contents.append(types.Content(
                        role="user" if msg.role == "user" else "model",
                        parts=[types.Part.from_text(text=msg.content)]
                    ))
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=user_message)]
                ))

                config = types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    tools=TOOL_FUNCTIONS,
                    temperature=0.3
                )

                # First call to model
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=config
                )

                # Check for function calls
                function_calls = response.function_calls
                if function_calls:
                    # Model requested one or more tool executions
                    tool_parts = []
                    for call in function_calls:
                        fn_name = call.name
                        fn_args = dict(call.args) if call.args else {}
                        
                        tool_result = self.execute_tool(fn_name, fn_args)
                        tool_executions.append(ToolExecutionDetail(
                            tool_name=fn_name,
                            arguments=fn_args,
                            result=tool_result
                        ))

                        tool_parts.append(types.Part.from_function_response(
                            name=fn_name,
                            response={"result": tool_result}
                        ))

                    # Provide tool results back to the model for final synthesis
                    contents.append(response.candidates[0].content)
                    contents.append(types.Content(role="tool", parts=tool_parts))

                    final_response = self.client.models.generate_content(
                        model=self.model_name,
                        contents=contents,
                        config=config
                    )
                    return final_response.text or "I processed your request.", tool_executions
                
                return response.text or "How can I help with your delivery today?", tool_executions

            except Exception as e:
                logger.error("Error during live Gemini execution: %s", e)
                # Graceful degradation to intelligent mock rule engine
                return self._mock_reasoning_engine(user_message, tool_executions)

        # Smart fallback mode (enables instant testing before setting API key)
        return self._mock_reasoning_engine(user_message, tool_executions)

    def _mock_reasoning_engine(self, user_message: str, tool_executions: List[ToolExecutionDetail]) -> Tuple[str, List[ToolExecutionDetail]]:
        """Intelligent rule-based simulation engine for instant testing without an active API key."""
        msg_lower = user_message.lower()
        
        # Detect Order ID in message
        detected_order_id = None
        for oid in ["ORD-1001", "ORD-1002", "ORD-1003", "ORD-1004"]:
            if oid.lower() in msg_lower:
                detected_order_id = oid
                break

        # Scenario 1: Tracking / Status
        if any(w in msg_lower for w in ["track", "status", "where is", "where's", "eta", "when will"]) or (detected_order_id and "cancel" not in msg_lower and "refund" not in msg_lower and "damaged" not in msg_lower and "missing" not in msg_lower):
            order_id = detected_order_id or "ORD-1001"
            result = self.execute_tool("get_order_status", {"order_id": order_id})
            tool_executions.append(ToolExecutionDetail(tool_name="get_order_status", arguments={"order_id": order_id}, result=result))
            
            if not result.get("success"):
                return f"I couldn't locate order **{order_id}**. Could you double-check your receipt or order history?", tool_executions
            
            if result.get("status") == "Delivered":
                return f"Your order **{order_id}** from **{result['restaurant']}** was delivered {result.get('delivered_at', 'recently')}. Please check your front door or front desk. Let me know if you need help with missing or damaged items!", tool_executions
            
            courier = result.get("courier", {})
            driver_info = f" Courier **{courier.get('name')}** ({courier.get('vehicle')}) is currently {courier.get('current_location')}." if courier else ""
            return f"Order **{order_id}** from **{result['restaurant']}** is currently **{result['status']}**! 🛵\n\n- **ETA:** ~{result.get('eta_minutes')} minutes\n- **Delivery Address:** {result['delivery_address']}{driver_info}", tool_executions

        # Scenario 2: Returns / Refunds / Replacements / Food Issues
        if any(w in msg_lower for w in ["return", "refund", "replace", "send back", "damaged", "missing", "cold", "ruined", "broken", "spilled", "wrong"]):
            if not detected_order_id:
                policy_res = self.execute_tool("get_delivery_policy", {"topic": "refund_and_replacement"})
                tool_executions.append(ToolExecutionDetail(
                    tool_name="get_delivery_policy",
                    arguments={"topic": "refund_and_replacement"},
                    result=policy_res
                ))
                return (
                    "I can certainly help you with returning or refunding your order! 🍕\n\n"
                    "**Policy Notice:** Under food safety regulations, prepared food deliveries cannot be physically returned or picked back up. "
                    "However, you are 100% eligible for an **instant refund or delivery wallet credit** if your food was missing, cold, spoiled, or damaged.\n\n"
                    "👉 **Please provide your Order ID** (e.g., `ORD-1002`) and tell me what went wrong so I can process your compensation immediately!"
                ), tool_executions

            order_id = detected_order_id
            issue_type = "damaged_item" if ("damaged" in msg_lower or "spilled" in msg_lower) else ("missing_item" if "missing" in msg_lower else "return_request")
            
            # 1. Report issue tool
            rep_res = self.execute_tool("report_delivery_issue", {
                "order_id": order_id,
                "issue_type": issue_type,
                "details": user_message
            })
            tool_executions.append(ToolExecutionDetail(tool_name="report_delivery_issue", arguments={"order_id": order_id, "issue_type": issue_type, "details": user_message}, result=rep_res))
            
            # 2. Process refund tool
            ref_res = self.execute_tool("process_refund_or_credit", {
                "order_id": order_id,
                "reason": f"Customer requested return/refund ({issue_type})",
                "amount": 18.00,
                "refund_method": "delivery_wallet"
            })
            tool_executions.append(ToolExecutionDetail(tool_name="process_refund_or_credit", arguments={"order_id": order_id, "reason": f"Customer requested return/refund"}, result=ref_res))
            
            return (
                f"I have processed your request for order **{order_id}**! 💸\n\n"
                f"- **Incident Report:** `{rep_res.get('report_id')}` registered.\n"
                f"- **Refund Processed:** **$18.00** credited to your SwiftDrop Delivery Wallet (Txn: `{ref_res.get('transaction_id')}`).\n"
                f"- Since prepared food cannot be collected back, you do not need to return the items."
            ), tool_executions

        # Scenario 3: Change Address or Delivery Notes
        if any(w in msg_lower for w in ["address", "gate code", "instruction", "drop off", "porch", "leave at", "door"]):
            order_id = detected_order_id or "ORD-1003"
            res = self.execute_tool("update_delivery_address", {
                "order_id": order_id,
                "delivery_notes": "Please leave at front door, ring doorbell once."
            })
            tool_executions.append(ToolExecutionDetail(tool_name="update_delivery_address", arguments={"order_id": order_id, "delivery_notes": "Please leave at front door..."}, result=res))
            
            if res.get("success"):
                return f"I have updated the delivery notes for **{order_id}**: *\"{res.get('updated_notes')}\"*. Your driver will see this immediately!", tool_executions
            else:
                return f"Notice for **{order_id}**: {res.get('message', res.get('error'))}", tool_executions

        # Scenario 4: Policy questions
        if any(w in msg_lower for w in ["policy", "cancel", "refund policy", "late fee", "compensation", "hours"]):
            topic = "cancellation" if "cancel" in msg_lower else ("delivery_delay" if "late" in msg_lower or "delay" in msg_lower else "refund_and_replacement")
            res = self.execute_tool("get_delivery_policy", {"topic": topic})
            tool_executions.append(ToolExecutionDetail(tool_name="get_delivery_policy", arguments={"topic": topic}, result=res))
            return f"Here is our policy on **{topic.replace('_', ' ').title()}**:\n\n{res.get('policy')}", tool_executions

        # Scenario 5: Escalation / Human Agent
        if any(w in msg_lower for w in ["human", "agent", "supervisor", "representative", "speak to someone", "angry", "terrible", "lawsuit"]):
            order_id = detected_order_id or "ORD-1001"
            res = self.execute_tool("escalate_to_human_agent", {
                "order_id": order_id,
                "summary": user_message,
                "customer_sentiment": "frustrated"
            })
            tool_executions.append(ToolExecutionDetail(tool_name="escalate_to_human_agent", arguments={"order_id": order_id, "summary": user_message}, result=res))
            return (
                f"I completely understand and I'm escalating your case to a human specialist right away. 👤\n\n"
                f"- **Ticket Number:** {res.get('ticket_id')}\n"
                f"- **Queue Position:** #{res.get('queue_position')}\n"
                f"- **Assigned Specialist:** {res.get('agent_name')}\n"
                f"- **Estimated Wait:** ~1 minute. Please stay on this screen!"
            ), tool_executions

        # General Welcome / Fallback
        return (
            "Hello! I am your **SwiftDrop Delivery Assistant** 🛵. How can I help you today?\n\n"
            "Here are a few things you can ask me:\n"
            "- *\"Track order ORD-1001\"* (Live courier status & ETA)\n"
            "- *\"My burger in ORD-1002 was damaged\"* (Instant resolution & refund)\n"
            "- *\"Change drop-off notes for ORD-1003\"* (Doorbell/gate code updates)\n"
            "- *\"What is your cancellation policy?\"*\n"
            "- *\"I want to speak with a human agent\"*"
        ), tool_executions
