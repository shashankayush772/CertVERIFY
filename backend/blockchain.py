"""
CertVerify — Polygon Amoy blockchain anchoring.
Stores certificate hashes on-chain for immutable verification.
"""

from __future__ import annotations

import os
from typing import Optional

# ── Configuration ────────────────────────────────────────────────────────────
# All sensitive blockchain values must come from environment variables.
ALCHEMY_URL = os.environ.get("CERTVERIFY_ALCHEMY_URL", "")
CONTRACT_ADDRESS = os.environ.get("CERTVERIFY_CONTRACT_ADDRESS", "")
WALLET_PRIVATE_KEY = os.environ.get("CERTVERIFY_PRIVATE_KEY", "")
WALLET_ADDRESS = os.environ.get("CERTVERIFY_WALLET_ADDRESS", "")

# Contract ABI — paste your ABI here
CONTRACT_ABI = [
	{
		"inputs": [],
		"stateMutability": "nonpayable",
		"type": "constructor"
	},
	{
		"anonymous": False,
		"inputs": [
			{
				"indexed": False,
				"internalType": "string",
				"name": "certId",
				"type": "string"
			},
			{
				"indexed": False,
				"internalType": "uint256",
				"name": "timestamp",
				"type": "uint256"
			}
		],
		"name": "CertificateRevoked",
		"type": "event"
	},
	{
		"anonymous": False,
		"inputs": [
			{
				"indexed": False,
				"internalType": "string",
				"name": "certId",
				"type": "string"
			},
			{
				"indexed": False,
				"internalType": "string",
				"name": "hash",
				"type": "string"
			},
			{
				"indexed": False,
				"internalType": "uint256",
				"name": "timestamp",
				"type": "uint256"
			}
		],
		"name": "CertificateStored",
		"type": "event"
	},
	{
		"inputs": [
			{
				"internalType": "string",
				"name": "certId",
				"type": "string"
			}
		],
		"name": "revokeHash",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "string",
				"name": "certId",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "hash",
				"type": "string"
			}
		],
		"name": "storeHash",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "string",
				"name": "certId",
				"type": "string"
			}
		],
		"name": "certExists",
		"outputs": [
			{
				"internalType": "bool",
				"name": "",
				"type": "bool"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "string",
				"name": "certId",
				"type": "string"
			}
		],
		"name": "getHash",
		"outputs": [
			{
				"internalType": "string",
				"name": "",
				"type": "string"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "string",
				"name": "certId",
				"type": "string"
			}
		],
		"name": "getTimestamp",
		"outputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "owner",
		"outputs": [
			{
				"internalType": "address",
				"name": "",
				"type": "address"
			}
		],
		"stateMutability": "view",
		"type": "function"
	}
]

# ── Blockchain client ─────────────────────────────────────────────────────────

_web3 = None
_contract = None
_blockchain_enabled = False


def _get_web3():
    """Initialize Web3 connection. Returns None if not configured."""
    global _web3, _contract, _blockchain_enabled

    if _web3 is not None:
        return _web3

    # If any required value is missing, disable blockchain gracefully.
    if not all([ALCHEMY_URL, CONTRACT_ADDRESS, WALLET_PRIVATE_KEY, WALLET_ADDRESS]):
        print("[Blockchain] Not configured — blockchain anchoring disabled")
        print("[Blockchain] Set CERTVERIFY_ALCHEMY_URL, CERTVERIFY_CONTRACT_ADDRESS,")
        print("[Blockchain] CERTVERIFY_PRIVATE_KEY, CERTVERIFY_WALLET_ADDRESS to enable")
        return None

    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(ALCHEMY_URL))

        if not w3.is_connected():
            print("[Blockchain] WARNING: Could not connect to Polygon Amoy")
            return None

        contract = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACT_ADDRESS),
            abi=CONTRACT_ABI
        )

        _web3 = w3
        _contract = contract
        _blockchain_enabled = True
        print(f"[Blockchain] Connected to Polygon Amoy")
        print(f"[Blockchain] Contract: {CONTRACT_ADDRESS}")
        return _web3

    except Exception as e:
        print(f"[Blockchain] Connection failed (non-fatal): {e}")
        return None


def store_hash_on_chain(cert_id: int, cert_hash: str) -> Optional[str]:
    """
    Store a certificate hash on the Polygon blockchain.
    Returns the transaction hash if successful, None if blockchain is disabled.
    This is NON-BLOCKING — if blockchain fails, certificate issuance still works.
    """
    try:
        w3 = _get_web3()
        if w3 is None or _contract is None:
            return None

        from web3 import Web3

        cert_id_str = str(cert_id)

        # Build transaction
        nonce = w3.eth.get_transaction_count(
            Web3.to_checksum_address(WALLET_ADDRESS)
        )

        # Cap gas price to avoid overspending on testnet (min 25 gwei for Amoy)
        gas_price = max(w3.to_wei(25, "gwei"), min(w3.eth.gas_price, w3.to_wei(35, "gwei")))

        tx = _contract.functions.storeHash(
            cert_id_str,
            cert_hash
        ).build_transaction({
            "from": Web3.to_checksum_address(WALLET_ADDRESS),
            "nonce": nonce,
            "gas": 200000,
            "gasPrice": gas_price,
            "chainId": 80002  # Polygon Amoy
        })

        # Sign and send
        signed = w3.eth.account.sign_transaction(tx, WALLET_PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        tx_hash_hex = tx_hash.hex()

        print(f"[Blockchain] Hash stored on chain. TX: {tx_hash_hex}")
        print(f"[Blockchain] View: https://amoy.polygonscan.com/tx/{tx_hash_hex}")

        return tx_hash_hex

    except Exception as e:
        print(f"[Blockchain] store_hash_on_chain failed (non-fatal): {e}")
        return None


def verify_hash_on_chain(cert_id: int, cert_hash: str) -> dict:
    """
    Verify a certificate hash against the blockchain record.
    Returns a dict with status and details.
    Always returns a result — never crashes the server.
    Uses multiple RPC endpoints as fallback for read consistency.
    """
    import time

    try:
        w3 = _get_web3()
        if w3 is None or _contract is None:
            return {
                "status": "DISABLED",
                "detail": "Blockchain verification not configured",
                "matches": None
            }

        from web3 import Web3
        cert_id_str = str(cert_id)

        # Try multiple RPC endpoints for read consistency
        rpc_urls = [
            ALCHEMY_URL,
            "https://polygon-amoy-bor-rpc.publicnode.com",
            "https://rpc-amoy.polygon.technology/",
            "https://polygon-amoy.drpc.org",
        ]
        # Remove duplicates while preserving order
        seen = set()
        unique_rpcs = []
        for url in rpc_urls:
            if url and url not in seen:
                seen.add(url)
                unique_rpcs.append(url)

        print(f"[Blockchain] Verifying cert {cert_id_str} on chain...")

        for attempt, rpc_url in enumerate(unique_rpcs):
            try:
                read_w3 = Web3(Web3.HTTPProvider(rpc_url))
                if not read_w3.is_connected():
                    continue

                read_contract = read_w3.eth.contract(
                    address=Web3.to_checksum_address(CONTRACT_ADDRESS),
                    abi=CONTRACT_ABI,
                )

                exists = read_contract.functions.certExists(cert_id_str).call()
                if not exists:
                    # RPC might be stale — try next one
                    print(f"[Blockchain] RPC {rpc_url} says NOT_FOUND, trying next...")
                    continue

                # Found! Get stored hash
                chain_hash = read_contract.functions.getHash(cert_id_str).call()

                if chain_hash == "REVOKED":
                    return {
                        "status": "REVOKED",
                        "detail": "Certificate has been revoked on blockchain",
                        "matches": False
                    }

                matches = chain_hash.lower() == cert_hash.lower()

                if matches:
                    timestamp = read_contract.functions.getTimestamp(cert_id_str).call()
                    return {
                        "status": "VERIFIED",
                        "detail": "Hash matches blockchain record",
                        "matches": True,
                        "chain_hash": chain_hash,
                        "timestamp": timestamp,
                        "explorer_url": f"https://amoy.polygonscan.com/address/{CONTRACT_ADDRESS}"
                    }
                else:
                    return {
                        "status": "MISMATCH",
                        "detail": "Hash does not match blockchain record",
                        "matches": False,
                        "chain_hash": chain_hash,
                        "submitted_hash": cert_hash
                    }

            except Exception as rpc_err:
                print(f"[Blockchain] RPC {rpc_url} failed: {rpc_err}")
                continue

        # All RPCs returned NOT_FOUND — maybe the TX hasn't propagated yet
        # Wait briefly and try once more with the primary RPC
        print("[Blockchain] All RPCs returned NOT_FOUND, waiting 3s and retrying...")
        time.sleep(3)

        try:
            exists = _contract.functions.certExists(cert_id_str).call()
            if exists:
                chain_hash = _contract.functions.getHash(cert_id_str).call()
                if chain_hash == "REVOKED":
                    return {"status": "REVOKED", "detail": "Certificate has been revoked on blockchain", "matches": False}
                matches = chain_hash.lower() == cert_hash.lower()
                if matches:
                    timestamp = _contract.functions.getTimestamp(cert_id_str).call()
                    return {
                        "status": "VERIFIED", "detail": "Hash matches blockchain record",
                        "matches": True, "chain_hash": chain_hash, "timestamp": timestamp,
                        "explorer_url": f"https://amoy.polygonscan.com/address/{CONTRACT_ADDRESS}"
                    }
                return {"status": "MISMATCH", "detail": "Hash does not match blockchain record",
                        "matches": False, "chain_hash": chain_hash, "submitted_hash": cert_hash}
        except Exception:
            pass

        return {
            "status": "NOT_FOUND",
            "detail": "Certificate hash not found on blockchain",
            "matches": False
        }

    except Exception as e:
        import traceback
        print(f"[Blockchain] verify_hash_on_chain failed (non-fatal): {e}")
        traceback.print_exc()
        return {
            "status": "ERROR",
            "detail": f"Blockchain check failed: {str(e)}",
            "matches": None
        }


def is_blockchain_enabled() -> bool:
    """Check if blockchain is configured and connected."""
    return _get_web3() is not None