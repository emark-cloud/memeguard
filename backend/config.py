"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # BSC
    bsc_rpc_url: str = Field(default="https://bsc-dataseed1.binance.org")

    # Four.meme CLI
    private_key: str = Field(default="")
    fourmeme_cli_path: str = Field(default="npx fourmeme")

    # LLM
    gemini_api_key: str = Field(default="")

    # Database
    database_path: str = Field(default="./data/fourscout.db")

    # Scanner
    scan_interval_seconds: int = Field(default=30)

    # Four.meme API
    fourmeme_api_base: str = Field(default="https://four.meme/meme-api/v1")

    # LLM cost controls
    ai_exit_interval_cycles: int = Field(default=10)

    # Deployment: auth + CORS. Comma-separated list of allowed origins.
    # Empty api_key disables auth (single-tenant local dev).
    allowed_origins: str = Field(default="http://localhost:5173,http://localhost:3000")
    api_key: str = Field(default="")

    model_config = {"env_file": [".env", "../.env"], "env_file_encoding": "utf-8"}


settings = Settings()


# Contract addresses (BSC Mainnet) - these are fixed, not configurable
class Contracts:
    TOKEN_MANAGER_V2 = "0x5c952063c7fc8610FFDB798152D69F0B9550762b"
    TOKEN_MANAGER_HELPER3 = "0xF251F83e40a78868FcfA3FA4599Dad6494E46034"
    AGENT_IDENTIFIER = "0x09B44A633de9F9EBF6FB9Bdd5b5629d3DD2cef13"
    PANCAKE_ROUTER_V2 = "0x10ED43C718714eb63d5aA57B78B54704E256024E"
    WBNB = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
    BRC8004_REGISTRY = "0xfA09B3397fAC75424422C4D28b1729E3D4f659D7"
    TOKEN_MANAGER_V1 = "0xEC4549caDcE5DA21Df6E6422d448034B5233bFbC"
    # ERC-8004 standard Identity Registry (ERC-721Enumerable) — where
    # `fourmeme 8004-register` actually mints the agent NFT.
    ERC8004_IDENTITY_REGISTRY = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"


# Budget defaults
class BudgetDefaults:
    MAX_PER_TRADE_BNB = 0.05
    MAX_PER_DAY_BNB = 0.3
    MAX_ACTIVE_POSITIONS = 3
    MAX_TRADES_PER_TOKEN = 1
    MIN_LIQUIDITY_USD = 500
    MAX_SLIPPAGE_PCT = 5.0
    COOLDOWN_SECONDS = 60
