from web3 import Web3
import json
import time
from colorama import Fore, Style, init

init(autoreset=True)

# --- RPC URL ---
RPC_URL = "https://testnet.dplabs-internal.com"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# --- Token & Contract Addresses ---
USDT_ADDRESS = w3.to_checksum_address("0xd4071393f8716661958f766df660033b3d35fd29")
BTIVERSE_CONTRACT = w3.to_checksum_address("0xa307ce75bc6ef22794410d783e5d4265ded1a24f")

# --- ERC20 ABI fragment for approve ---
ERC20_ABI = json.loads("""
[
  {
    "constant": false,
    "inputs": [
      { "name": "spender", "type": "address" },
      { "name": "value", "type": "uint256" }
    ],
    "name": "approve",
    "outputs": [{ "name": "", "type": "bool" }],
    "type": "function"
  }
]
""")

# --- Platform Contract ABI fragment for deposit ---
PLATFORM_ABI = json.loads("""
[
  {
    "inputs": [
      { "internalType": "address", "name": "token", "type": "address" },
      { "internalType": "uint256", "name": "amount", "type": "uint256" }
    ],
    "name": "deposit",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  }
]
""")

# --- Load private keys ---
with open("pvt.txt", "r") as f:
    private_keys = [line.strip() for line in f if line.strip()]

# --- Input deposit amount ---
amount_input = float(input(f"{Fore.CYAN}Enter USDT amount to deposit: {Style.RESET_ALL} "))
# Convert to smallest unit (assuming USDT has 6 decimals)
amount = int(amount_input * 10**6)

# --- Helper to send transaction with retry ---
def send_txn(txn, pk, description):
    while True:
        try:
            signed_txn = w3.eth.account.sign_transaction(txn, private_key=pk)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            print(f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} {description} | TxHash: {w3.to_hex(tx_hash)}")
            # Wait for transaction receipt
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            if receipt.status == 1:
                return receipt
            else:
                raise Exception("Transaction failed on-chain")
        except Exception as e:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {description} | Reason: {e}")
            print(f"{Fore.YELLOW}Retrying in 10 seconds...{Style.RESET_ALL}")
            time.sleep(10)

# --- Loop through wallets ---
for pk in private_keys:
    account = w3.eth.account.from_key(pk)
    address = account.address
    print(f"\n{Fore.MAGENTA}🔑 Using wallet: {address}{Style.RESET_ALL}")

    # --- Approve USDT ---
    usdt_contract = w3.eth.contract(address=USDT_ADDRESS, abi=ERC20_ABI)
    nonce = w3.eth.get_transaction_count(address)
    approve_txn = usdt_contract.functions.approve(BTIVERSE_CONTRACT, amount).build_transaction({
        'chainId': w3.eth.chain_id,
        'gas': 100000,
        'gasPrice': w3.to_wei('3', 'gwei'),
        'nonce': nonce,
    })
    send_txn(approve_txn, pk, "Approve USDT Spending")

    # --- Deposit USDT ---
    platform_contract = w3.eth.contract(address=BTIVERSE_CONTRACT, abi=PLATFORM_ABI)
    nonce += 1
    deposit_txn = platform_contract.functions.deposit(USDT_ADDRESS, amount).build_transaction({
        'chainId': w3.eth.chain_id,
        'gas': 150000,
        'gasPrice': w3.to_wei('3', 'gwei'),
        'nonce': nonce,
    })
    send_txn(deposit_txn, pk, f"Deposit {amount_input} USDT")
