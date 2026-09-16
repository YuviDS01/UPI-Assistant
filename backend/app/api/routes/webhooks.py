"""
Placeholder for a real payment provider's server-to-server callback (e.g.
Paytm's payment status webhook). NOT wired to a working provider yet —
PaytmSandboxProvider.execute_payment isn't implemented (Phase 13). This
exists now to establish the fail-closed pattern before any real callback
is ever trusted: an unverified signature means the payload is refused
outright, not "processed cautiously."

CRITICAL: when a real provider is wired in, this must verify the callback
signature using that provider's official checksum utility BEFORE reading
any field from the body — a forged callback claiming "payment succeeded"
must never be able to mark a transaction SUCCESS on say-so alone.
"""

from fastapi import APIRouter, Request

from app.core.exceptions import ValidationAppError

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/paytm/callback")
async def paytm_callback(request: Request) -> dict:
    body = await request.json()
    signature = body.get("head", {}).get("signature")

    if not signature:
        raise ValidationAppError("Missing callback signature — refusing to process.")

    # TODO (Phase 13+, once real Paytm credentials + checksum utility exist):
    # verify `signature` against the body using Paytm's official checksum
    # tool. Until that's wired in, we deliberately do nothing with this
    # payload's contents — trusting it would let anyone POST a fake
    # "payment succeeded" callback and have it believed.
    raise NotImplementedError(
        "Callback signature verification is not implemented yet. This endpoint "
        "intentionally refuses to act on any callback until that's wired in."
    )