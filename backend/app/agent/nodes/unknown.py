from app.agent.state import PaymentState


def unknown_node(state: PaymentState) -> dict:
    return {
        "response": (
            "I can help with recurring payments, one-off payment approvals, and pausing/"
            "resuming mandates — could you rephrase what you'd like to do?"
        )
    }