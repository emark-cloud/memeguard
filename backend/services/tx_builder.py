"""Transaction builder — prepares trade previews with quotes and slippage calculations."""

import json
from dataclasses import dataclass, asdict


@dataclass
class TxPreview:
    action_type: str  # buy / sell
    token_address: str
    amount_bnb: float
    estimated_tokens: float
    estimated_price: float
    slippage_pct: float
    min_tokens: float  # after slippage
    quote_raw: dict


async def build_buy_preview(
    token_address: str,
    amount_bnb: float,
    slippage_pct: float = 5.0,
) -> TxPreview:
    """Get a buy quote and build a transaction preview."""
    from clients.fourmeme_cli import FourMemeCLI

    cli = FourMemeCLI()
    funds_wei = str(int(amount_bnb * 10**18))

    try:
        quote = await cli.quote_buy(token_address, "0", funds_wei)
    except Exception as e:
        # Return preview with zero estimates if quote fails
        return TxPreview(
            action_type="buy",
            token_address=token_address,
            amount_bnb=amount_bnb,
            estimated_tokens=0,
            estimated_price=0,
            slippage_pct=slippage_pct,
            min_tokens=0,
            quote_raw={"error": str(e)},
        )

    estimated_tokens_wei = int(quote.get("estimatedAmount", 0) or 0)
    estimated_tokens = estimated_tokens_wei / 10**18
    # Price in BNB per token
    estimated_price = (amount_bnb / estimated_tokens) if estimated_tokens > 0 else 0
    min_tokens = estimated_tokens * (1 - slippage_pct / 100)

    return TxPreview(
        action_type="buy",
        token_address=token_address,
        amount_bnb=amount_bnb,
        estimated_tokens=estimated_tokens,
        estimated_price=estimated_price,
        slippage_pct=slippage_pct,
        min_tokens=min_tokens,
        quote_raw=quote,
    )


async def build_sell_preview(
    token_address: str,
    token_amount: float,
    slippage_pct: float = 5.0,
) -> TxPreview:
    """Get a sell quote and build a transaction preview."""
    from clients.fourmeme_cli import FourMemeCLI

    cli = FourMemeCLI()
    amount_wei = str(int(token_amount * 10**18))

    try:
        quote = await cli.quote_sell(token_address, amount_wei)
    except Exception as e:
        return TxPreview(
            action_type="sell",
            token_address=token_address,
            amount_bnb=0,
            estimated_tokens=token_amount,
            estimated_price=0,
            slippage_pct=slippage_pct,
            min_tokens=0,
            quote_raw={"error": str(e)},
        )

    estimated_bnb = float(quote.get("funds", 0) or quote.get("amount", 0) or 0) / 10**18
    estimated_price = (estimated_bnb / token_amount) if token_amount > 0 else 0

    return TxPreview(
        action_type="sell",
        token_address=token_address,
        amount_bnb=estimated_bnb,
        estimated_tokens=token_amount,
        estimated_price=estimated_price,
        slippage_pct=slippage_pct,
        min_tokens=0,
        quote_raw=quote,
    )


def preview_to_json(preview: TxPreview) -> str:
    """Serialize a TxPreview to JSON for storage in pending_actions.tx_preview."""
    return json.dumps(asdict(preview))
