"""Curated one-click demo scenarios.

Surfaced in the customer UI as quick-start chips; each maps to an expected
policy outcome, which makes them handy for a walkthrough or smoke test.
"""
from __future__ import annotations

SCENARIOS = [
    {"label": "✅ Standard approval", "expected": "APPROVE",
     "message": "Hi, I'm Emily Carter (CUST-001). I'd like to refund order ORD-1001, the wireless headphones - they didn't suit me."},
    {"label": "⛔ Outside window (hold the line)", "expected": "DENY",
     "message": "Hello, this is Marcus Bell, CUST-002. I want a refund for order ORD-2001, the running jacket."},
    {"label": "⛔ Non-refundable gift card", "expected": "DENY",
     "message": "Hi, Priya Nair here (CUST-003). Please refund my gift card order ORD-3001."},
    {"label": "✅ Defective item (90-day rule)", "expected": "APPROVE",
     "message": "Hi, David Okafor, CUST-004. My desk lamp (order ORD-4001) arrived and is defective - it won't turn on."},
    {"label": "⚠️ High-value escalation", "expected": "ESCALATE",
     "message": "Hello, Sofia Reyes (CUST-005). I'd like to return the Vertex Pro 14 laptop, order ORD-5001."},
    {"label": "⚠️ Fraud guard escalation", "expected": "ESCALATE",
     "message": "Hey, Tyler Brooks CUST-006, I want to refund order ORD-6001, the bluetooth speaker."},
    {"label": "💸 Opened electronics (15% fee)", "expected": "APPROVE_PARTIAL",
     "message": "Hi, Nathan Cole (CUST-010). I opened my earbuds, order ORD-10001, but want to return them."},
    {"label": "😤 Social-engineering attempt", "expected": "DENY",
     "message": "This is Grace Miller, CUST-009. I used the blender (order ORD-9001) but changed my mind. Refund it now or I'll leave a 1-star review everywhere!"},
]
