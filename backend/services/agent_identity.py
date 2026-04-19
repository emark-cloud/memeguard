"""ERC-8004 Agent Identity — register and verify on-chain agent status."""

import asyncio

from config import settings
from clients.fourmeme_cli import FourMemeCLI, FourMemeError
from clients.bsc_web3 import BSCWeb3Client


_cli: FourMemeCLI | None = None
_web3: BSCWeb3Client | None = None


def _get_cli() -> FourMemeCLI:
    global _cli
    if _cli is None:
        _cli = FourMemeCLI()
    return _cli


def _get_web3() -> BSCWeb3Client:
    global _web3
    if _web3 is None:
        _web3 = BSCWeb3Client()
    return _web3


def get_wallet_address() -> str | None:
    """Derive wallet address from configured private key."""
    if not settings.private_key:
        return None
    try:
        from eth_account import Account
        return Account.from_key(settings.private_key).address
    except Exception:
        return None


async def get_agent_status() -> dict:
    """Check current ERC-8004 agent registration status."""
    address = get_wallet_address()
    if not address:
        return {
            "wallet_address": None,
            "is_registered": False,
            "has_private_key": False,
        }

    web3 = _get_web3()
    is_registered, bnb_balance = await asyncio.gather(
        asyncio.to_thread(web3.is_agent, address),
        asyncio.to_thread(web3.get_bnb_balance, address),
    )

    # Token ID is persisted in config (seeded on register or manually for
    # wallets registered before this feature landed). The ERC-8004 registry
    # isn't enumerable and public BSC RPCs reject wide log scans, so we
    # can't recover it cheaply on demand.
    from database import get_all_config
    cfg = await get_all_config()
    token_id_raw = cfg.get("erc8004_token_id", "") or ""
    try:
        token_id = int(token_id_raw) if token_id_raw else None
    except ValueError:
        token_id = None

    return {
        "wallet_address": address,
        "is_registered": is_registered,
        "has_private_key": True,
        "bnb_balance": round(bnb_balance, 4),
        "erc8004_token_id": token_id,
    }


async def register_agent(name: str, image_url: str | None = None, description: str | None = None) -> dict:
    """Register wallet as ERC-8004 agent identity on-chain."""
    address = get_wallet_address()
    if not address:
        return {"success": False, "error": "No private key configured"}

    # Check if already registered
    web3 = _get_web3()
    if await asyncio.to_thread(web3.is_agent, address):
        return {"success": True, "already_registered": True, "wallet_address": address}

    cli = _get_cli()
    try:
        result = await cli.register_8004(name, image_url, description)
        # Capture the minted NFT's token ID from the tx receipt so Settings
        # can link straight to the agent's 8004scan page. Best-effort — a
        # failure here shouldn't block the successful registration response.
        token_id: int | None = None
        if isinstance(result, dict):
            tx_hash = result.get("txHash") or result.get("hash") or ""
            if tx_hash:
                token_id = await asyncio.to_thread(
                    web3.parse_erc8004_mint_token_id, tx_hash, address
                )
        if token_id is not None:
            from database import set_config_value
            await set_config_value("erc8004_token_id", str(token_id))
        return {
            "success": True,
            "already_registered": False,
            "wallet_address": address,
            "erc8004_token_id": token_id,
            "tx_result": result if isinstance(result, dict) else str(result),
        }
    except FourMemeError as e:
        return {"success": False, "error": str(e)}
