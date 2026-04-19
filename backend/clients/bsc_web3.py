"""Direct Web3.py client for BSC on-chain reads used in risk scoring."""

import json
from pathlib import Path
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from config import settings, Contracts

ABI_DIR = Path(__file__).resolve().parent.parent / "abis"


def _load_abi(name: str) -> list:
    with open(ABI_DIR / f"{name}.json") as f:
        return json.load(f)


class BSCWeb3Client:
    """Read-only BSC client for risk scoring data."""

    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(settings.bsc_rpc_url))
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        # Load ABIs
        self.erc20_abi = _load_abi("ERC20")
        self.token_manager2_abi = _load_abi("TokenManager2")
        self.helper3_abi = _load_abi("TokenManagerHelper3")
        self.agent_id_abi = _load_abi("AgentIdentifier")
        self.tax_token_abi = _load_abi("TaxToken")

        # Contract instances
        self.helper3 = self.w3.eth.contract(
            address=Web3.to_checksum_address(Contracts.TOKEN_MANAGER_HELPER3),
            abi=self.helper3_abi,
        )
        self.agent_identifier = self.w3.eth.contract(
            address=Web3.to_checksum_address(Contracts.AGENT_IDENTIFIER),
            abi=self.agent_id_abi,
        )
        self.token_manager2 = self.w3.eth.contract(
            address=Web3.to_checksum_address(Contracts.TOKEN_MANAGER_V2),
            abi=self.token_manager2_abi,
        )

    def get_token_info(self, token_address: str) -> dict:
        """Get token info from TokenManagerHelper3."""
        try:
            addr = Web3.to_checksum_address(token_address)
            try:
                info = self.helper3.functions.getTokenInfo(addr).call()
                return {
                    "version": info[0],
                    "tokenManager": info[1],
                    "quote": info[2],
                    "lastPrice": info[3],
                    "tradingFeeRate": info[4],
                    "launchTime": info[5],
                    "offers": info[6],
                    "maxOffers": info[7],
                    "funds": info[8],
                    "maxFunds": info[9],
                    "liquidityAdded": info[10],
                }
            except Exception:
                # V2 tokens return a 12-field struct (extra field at index 5)
                # that web3.py can't decode with the 11-field ABI. Raw decode.
                selector = self.w3.keccak(text="getTokenInfo(address)")[:4]
                padded = bytes.fromhex(addr[2:].zfill(64))
                raw = self.w3.eth.call({"to": self.helper3.address, "data": selector + padded})
                if len(raw) < 352:
                    return {}
                words = [int.from_bytes(raw[i : i + 32], "big") for i in range(0, len(raw), 32)]
                n = len(words)
                def _addr(val):
                    return Web3.to_checksum_address("0x" + hex(val)[2:].zfill(40)) if val else "0x" + "0" * 40
                if n >= 12:
                    # 12-field V2: extra field between tradingFeeRate and launchTime
                    return {
                        "version": words[0],
                        "tokenManager": _addr(words[1]),
                        "quote": _addr(words[2]),
                        "lastPrice": words[3],
                        "tradingFeeRate": words[4],
                        "launchTime": words[6],
                        "offers": words[7],
                        "maxOffers": words[8],
                        "funds": words[9],
                        "maxFunds": words[10],
                        "liquidityAdded": bool(words[11]),
                    }
                else:
                    # 11-field layout
                    return {
                        "version": words[0],
                        "tokenManager": _addr(words[1]),
                        "quote": _addr(words[2]),
                        "lastPrice": words[3],
                        "tradingFeeRate": words[4],
                        "launchTime": words[5],
                        "offers": words[6],
                        "maxOffers": words[7],
                        "funds": words[8],
                        "maxFunds": words[9],
                        "liquidityAdded": bool(words[10]),
                    }
        except Exception as e:
            print(f"[Web3] getTokenInfo error for {token_address}: {e}")
            return {}

    def get_token_balance(self, token_address: str) -> int | None:
        """Get the agent wallet's exact token balance (in wei) for selling."""
        try:
            addr = Web3.to_checksum_address(token_address)
            token_contract = self.w3.eth.contract(address=addr, abi=self.erc20_abi)
            from eth_account import Account
            wallet = Account.from_key(settings.private_key).address
            return token_contract.functions.balanceOf(Web3.to_checksum_address(wallet)).call()
        except Exception as e:
            print(f"[BSCWeb3] get_token_balance error: {e}")
            return None

    def get_holder_balances(self, token_address: str, top_n: int = 10) -> dict:
        """Get holder concentration data for a token.

        Returns top holders and concentration metrics.
        """
        try:
            addr = Web3.to_checksum_address(token_address)
            token_contract = self.w3.eth.contract(address=addr, abi=self.erc20_abi)

            total_supply = token_contract.functions.totalSupply().call()
            if total_supply == 0:
                return {"total_supply": 0, "holders": [], "top5_pct": 0, "max_single_pct": 0}

            # Get Transfer events to find holders (last 1000 blocks)
            current_block = self.w3.eth.block_number
            from_block = max(0, current_block - 1000)

            try:
                transfer_filter = token_contract.events.Transfer.create_filter(
                    fromBlock=from_block, toBlock="latest"
                )
                transfers = transfer_filter.get_all_entries()
            except Exception:
                # Fallback: return minimal data
                return {"total_supply": total_supply, "holders": [], "top5_pct": 0, "max_single_pct": 0}

            # Collect unique addresses (excluding zero and contract addresses)
            addresses = set()
            for t in transfers:
                addresses.add(t["args"]["to"])
                addresses.add(t["args"]["from"])
            addresses.discard("0x0000000000000000000000000000000000000000")

            # Get balances for each holder.
            # Cap at 20: public BSC RPCs rate-limit aggressively on back-to-back
            # eth_calls, and we already see RemoteDisconnected errors at 50.
            # Multicall3 upgrade is the proper fix; 20 is the stop-gap.
            balances = []
            for holder_addr in list(addresses)[:20]:
                try:
                    bal = token_contract.functions.balanceOf(holder_addr).call()
                    if bal > 0:
                        pct = (bal / total_supply) * 100
                        balances.append({"address": holder_addr, "balance": bal, "pct": round(pct, 2)})
                except Exception:
                    continue

            # Sort by balance descending
            balances.sort(key=lambda x: x["balance"], reverse=True)
            top = balances[:top_n]

            top5_pct = sum(h["pct"] for h in top[:5])
            max_single_pct = top[0]["pct"] if top else 0

            return {
                "total_supply": total_supply,
                "holders": top,
                "top5_pct": round(top5_pct, 2),
                "max_single_pct": round(max_single_pct, 2),
                "unique_holders": len(balances),
            }
        except Exception as e:
            print(f"[Web3] get_holder_balances error for {token_address}: {e}")
            return {"total_supply": 0, "holders": [], "top5_pct": 0, "max_single_pct": 0}

    def get_creator_history(self, creator_address: str) -> list:
        """Get tokens previously created by this address via TokenCreate events."""
        try:
            addr = Web3.to_checksum_address(creator_address)
            current_block = self.w3.eth.block_number
            from_block = max(0, current_block - 50000)  # ~2 days of blocks

            try:
                event_filter = self.token_manager2.events.TokenCreate.create_filter(
                    fromBlock=from_block,
                    toBlock="latest",
                    argument_filters={"creator": addr},
                )
                events = event_filter.get_all_entries()
            except Exception:
                return []

            return [
                {
                    "token": e["args"]["token"],
                    "name": e["args"].get("name", ""),
                    "symbol": e["args"].get("symbol", ""),
                    "block": e["blockNumber"],
                }
                for e in events
            ]
        except Exception as e:
            print(f"[Web3] get_creator_history error for {creator_address}: {e}")
            return []

    def is_tax_token(self, token_address: str) -> dict:
        """Check if token is a TaxToken and get fee parameters."""
        try:
            addr = Web3.to_checksum_address(token_address)
            token_contract = self.w3.eth.contract(address=addr, abi=self.tax_token_abi)

            fee_rate = token_contract.functions.feeRate().call()
            if fee_rate > 0:
                return {
                    "is_tax": True,
                    "fee_rate_bps": fee_rate,
                    "rate_founder": token_contract.functions.rateFounder().call(),
                    "rate_burn": token_contract.functions.rateBurn().call(),
                    "rate_liquidity": token_contract.functions.rateLiquidity().call(),
                }
            return {"is_tax": False, "fee_rate_bps": 0}
        except Exception:
            # Not a TaxToken contract or call failed
            return {"is_tax": False, "fee_rate_bps": 0}

    def is_agent(self, wallet_address: str) -> bool:
        """Check if wallet is registered as an ERC-8004 agent."""
        try:
            addr = Web3.to_checksum_address(wallet_address)
            return self.agent_identifier.functions.isAgent(addr).call()
        except Exception:
            return False

    def parse_erc8004_mint_token_id(self, tx_hash: str, wallet_address: str) -> int | None:
        """Extract the ERC-8004 agent NFT tokenId that was minted to
        `wallet_address` inside the given transaction. The Identity Registry
        is not ERC-721Enumerable and public BSC RPCs reject wide log scans,
        so we only look at this specific receipt's logs. Returns None if
        the mint log can't be located."""
        try:
            from hexbytes import HexBytes
            owner = Web3.to_checksum_address(wallet_address)
            receipt = self.w3.eth.get_transaction_receipt(HexBytes(tx_hash))
            transfer_topic = "0x" + self.w3.keccak(text="Transfer(address,address,uint256)").hex().lstrip("0x")
            zero_topic = "0x" + "0" * 64
            owner_topic = "0x" + owner[2:].lower().rjust(64, "0")
            for log in receipt["logs"]:
                if log["address"].lower() != Contracts.ERC8004_IDENTITY_REGISTRY.lower():
                    continue
                topics: list[str] = []
                for t in log["topics"]:
                    s = t.hex() if hasattr(t, "hex") else str(t)
                    topics.append("0x" + s.removeprefix("0x"))
                if len(topics) >= 4 and topics[0].lower() == transfer_topic.lower() \
                        and topics[1].lower() == zero_topic \
                        and topics[2].lower() == owner_topic.lower():
                    return int(topics[3], 16)
            return None
        except Exception:
            return None

    def get_bnb_balance(self, address: str) -> float:
        """Get BNB balance in ether units."""
        try:
            addr = Web3.to_checksum_address(address)
            balance_wei = self.w3.eth.get_balance(addr)
            return float(Web3.from_wei(balance_wei, "ether"))
        except Exception:
            return 0.0

    def get_block_number(self) -> int:
        """Get current block number."""
        return self.w3.eth.block_number
