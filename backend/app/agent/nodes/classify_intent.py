"""
Uses an LLM with structured output to classify intent and extract entities
in one call. This is the ONLY node that calls an LLM for understanding.

Which provider backs it is a config switch (LLM_PROVIDER), not a code
change — same swappable pattern as PaymentProvider.
"""

from pydantic import BaseModel, Field

from app.agent.prompts import AGENT_SYSTEM_PROMPT, INTENT_CLASSIFICATION_INSTRUCTIONS
from app.agent.state import PaymentState
from app.core.config import get_settings


class IntentClassification(BaseModel):
    intent: str = Field(description="One of the fixed intent labels.")
    merchant_name: str | None = Field(default=None)
    category: str | None = Field(default=None)
    amount: float | None = Field(default=None)
    frequency: str | None = Field(default=None, description="DAILY, WEEKLY, MONTHLY, or YEARLY")
    next_payment_date: str | None = Field(default=None, description="ISO date if stated")
    mandate_hint: str | None = Field(
        default=None, description="Any phrase identifying WHICH mandate, e.g. 'electricity', 'netflix'"
    )
    pause_until: str | None = Field(default=None, description="ISO date if the user gave an end date for a pause")
    reason: str | None = Field(default=None, description="Free-text reason the user gave, if any")


def _get_classifier():
    settings = get_settings()

    if settings.llm_provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model, google_api_key=settings.google_api_key, temperature=0
        )
    elif settings.llm_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        llm = ChatAnthropic(model=settings.claude_model, api_key=settings.anthropic_api_key, temperature=0)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER '{settings.llm_provider}'. Expected 'gemini' or 'anthropic'.")

    return llm.with_structured_output(IntentClassification)


def classify_intent(state: PaymentState) -> dict:
    classifier = _get_classifier()
    result: IntentClassification = classifier.invoke(
        [
            ("system", AGENT_SYSTEM_PROMPT + "\n\n" + INTENT_CLASSIFICATION_INSTRUCTIONS),
            ("human", state["message"]),
        ]
    )

    valid_intents = {
        "CREATE_MANDATE", "CANCEL_MANDATE", "PAUSE_MANDATE", "RESUME_MANDATE",
        "VIEW_MANDATES", "VIEW_UPCOMING", "VIEW_HISTORY", "NEW_PAYMENT",
        "RECURRING_PAYMENT", "UNKNOWN",
    }
    intent = result.intent if result.intent in valid_intents else "UNKNOWN"

    return {
        "intent": intent,
        "merchant_name": result.merchant_name,
        "category": result.category,
        "amount": result.amount,
        "frequency": result.frequency,
        "next_payment_date": result.next_payment_date,
        "reason": result.reason,
        "pause_until": result.pause_until,
        "context": {"mandate_hint": result.mandate_hint},
    }