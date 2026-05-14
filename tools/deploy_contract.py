"""
Deploy CertRegistry.sol to Polygon Amoy testnet.

Usage:
  python tools/deploy_contract.py

Requires:
  - web3 and py-solc-x installed
  - .env file with CERTVERIFY_PRIVATE_KEY and CERTVERIFY_WALLET_ADDRESS
    OR the script will generate a new wallet for you
"""

import json
import os
import sys

# Add parent to path so we can load .env
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from web3 import Web3
from solcx import compile_source, install_solc

# ── Config ──────────────────────────────────────────────────────────────────
AMOY_RPC = os.environ.get(
    "CERTVERIFY_ALCHEMY_URL",
    "https://rpc-amoy.polygon.technology/"
)
PRIVATE_KEY = os.environ.get("CERTVERIFY_PRIVATE_KEY", "")
WALLET_ADDRESS = os.environ.get("CERTVERIFY_WALLET_ADDRESS", "")
CHAIN_ID = 80002  # Polygon Amoy

CONTRACT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "contracts",
    "CertRegistry.sol",
)


def generate_wallet(w3: Web3):
    """Generate a brand new Ethereum wallet."""
    acct = w3.eth.account.create()
    print("\n" + "=" * 60)
    print("  NEW WALLET GENERATED")
    print("=" * 60)
    print(f"  Address:     {acct.address}")
    print(f"  Private Key: {acct.key.hex()}")
    print("=" * 60)
    print("\n[!] SAVE THESE! You will need them.")
    print("[!] Fund this wallet with testnet POL from:")
    print("    https://faucet.polygon.technology/")
    print("    (select Amoy network, paste your address)\n")
    return acct.address, acct.key.hex()


def compile_contract():
    """Compile CertRegistry.sol and return ABI + bytecode."""
    print("[1/4] Installing Solidity compiler...")
    install_solc("0.8.0")

    print("[2/4] Compiling CertRegistry.sol...")
    with open(CONTRACT_PATH, "r") as f:
        source = f.read()

    compiled = compile_source(
        source,
        output_values=["abi", "bin"],
        solc_version="0.8.0",
    )

    # Get the contract
    contract_id, contract_interface = list(compiled.items())[0]
    abi = contract_interface["abi"]
    bytecode = contract_interface["bin"]

    print(f"    Contract: {contract_id}")
    print(f"    ABI functions: {len(abi)}")
    return abi, bytecode


def deploy(w3: Web3, abi, bytecode, private_key: str, wallet_address: str):
    """Deploy the compiled contract to Polygon Amoy."""
    print("[3/4] Deploying to Polygon Amoy testnet...")

    contract = w3.eth.contract(abi=abi, bytecode=bytecode)

    # Check balance
    balance = w3.eth.get_balance(Web3.to_checksum_address(wallet_address))
    balance_pol = w3.from_wei(balance, "ether")
    print(f"    Wallet balance: {balance_pol} POL")

    if balance == 0:
        print("\n[ERROR] Wallet has 0 POL. You need testnet POL to deploy.")
        print("   Go to: https://faucet.polygon.technology/")
        print(f"   Paste your address: {wallet_address}")
        print("   Select 'Amoy' network, request POL tokens.")
        print("   Then run this script again.\n")
        sys.exit(1)

    nonce = w3.eth.get_transaction_count(Web3.to_checksum_address(wallet_address))

    # Use a modest gas price to fit within the faucet balance
    gas_price = max(w3.to_wei(25, "gwei"), min(w3.eth.gas_price, w3.to_wei(35, "gwei")))
    print(f"    Gas price: {w3.from_wei(gas_price, 'gwei')} gwei")

    tx = contract.constructor().build_transaction({
        "from": Web3.to_checksum_address(wallet_address),
        "nonce": nonce,
        "gas": 800000,
        "gasPrice": gas_price,
        "chainId": CHAIN_ID,
    })

    signed = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"    TX Hash: {tx_hash.hex()}")
    print("    Waiting for confirmation...")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    contract_address = receipt["contractAddress"]

    print(f"\n[OK] Contract deployed!")
    print(f"   Address: {contract_address}")
    print(f"   TX: https://amoy.polygonscan.com/tx/{tx_hash.hex()}")
    print(f"   Contract: https://amoy.polygonscan.com/address/{contract_address}")

    return contract_address


def update_env_file(wallet_address: str, private_key: str, contract_address: str, rpc_url: str):
    """Update the .env file with blockchain config."""
    env_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        ".env",
    )

    print("\n[4/4] Updating .env file...")

    if os.path.isfile(env_path):
        with open(env_path, "r") as f:
            content = f.read()
    else:
        content = ""

    replacements = {
        "CERTVERIFY_ALCHEMY_URL": rpc_url,
        "CERTVERIFY_CONTRACT_ADDRESS": contract_address,
        "CERTVERIFY_PRIVATE_KEY": private_key,
        "CERTVERIFY_WALLET_ADDRESS": wallet_address,
    }

    for key, value in replacements.items():
        import re
        pattern = rf"^{key}=.*$"
        replacement = f"{key}={value}"
        if re.search(pattern, content, re.MULTILINE):
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        else:
            content += f"\n{replacement}"

    with open(env_path, "w") as f:
        f.write(content)

    print("    .env updated with blockchain config!")
    print("\n" + "=" * 60)
    print("  BLOCKCHAIN SETUP COMPLETE!")
    print("=" * 60)
    print("  Restart the backend server for changes to take effect.")
    print("=" * 60 + "\n")


def main():
    print("\n[*] CertRegistry Deployment Script")
    print("=" * 40)

    # Connect to Amoy
    w3 = Web3(Web3.HTTPProvider(AMOY_RPC))
    if not w3.is_connected():
        print(f"[FAIL] Cannot connect to {AMOY_RPC}")
        print("   Try a different RPC URL.")
        sys.exit(1)
    print(f"[OK] Connected to Polygon Amoy (chain {w3.eth.chain_id})")

    # Wallet
    private_key = PRIVATE_KEY
    wallet_address = WALLET_ADDRESS

    if not private_key or not wallet_address:
        print("\nNo wallet configured. Generating a new one...")
        wallet_address, private_key = generate_wallet(w3)

        # Save immediately so user doesn't lose keys
        update_env_file(wallet_address, private_key, "", AMOY_RPC)

        print("Fund the wallet first, then run this script again to deploy.")
        sys.exit(0)

    # Compile
    abi, bytecode = compile_contract()

    # Deploy
    contract_address = deploy(w3, abi, bytecode, private_key, wallet_address)

    # Save ABI for reference
    abi_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "contracts",
        "CertRegistry_abi.json",
    )
    with open(abi_path, "w") as f:
        json.dump(abi, f, indent=2)
    print(f"    ABI saved to {abi_path}")

    # Update .env
    update_env_file(wallet_address, private_key, contract_address, AMOY_RPC)


if __name__ == "__main__":
    main()
