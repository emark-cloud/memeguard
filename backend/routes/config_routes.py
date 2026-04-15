"""Configuration endpoints."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from database import get_all_config, set_config_value

router = APIRouter(tags=["config"])


class ConfigUpdate(BaseModel):
    key: str
    value: str


@router.get("/config")
async def get_config():
    """Get all configuration values."""
    return await get_all_config()


@router.put("/config")
async def update_config(update: ConfigUpdate):
    """Update a configuration value."""
    valid_keys = {
        "persona", "approval_mode", "max_per_trade_bnb", "max_per_day_bnb",
        "max_active_positions", "max_slippage_pct", "cooldown_seconds",
        "min_liquidity_usd", "take_profit_pct", "stop_loss_pct", "auto_sell_enabled",
    }
    if update.key not in valid_keys:
        return JSONResponse(content={"error": f"Invalid config key. Valid keys: {sorted(valid_keys)}"}, status_code=400)

    await set_config_value(update.key, update.value)
    return {"status": "ok", "key": update.key, "value": update.value}


@router.put("/config/bulk")
async def update_config_bulk(updates: dict):
    """Update multiple configuration values at once."""
    for key, value in updates.items():
        await set_config_value(key, str(value))
    return {"status": "ok", "updated": list(updates.keys())}
