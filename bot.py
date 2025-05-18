import os
import time
import logging
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.rpc.api import Client
from solana.transaction import Transaction
from solana.system_program import TransferParams, transfer

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DEST_WALLET = PublicKey(os.getenv("DESTINATION_WALLET"))
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"
THRESHOLD_USD = 300
client = Client(SOLANA_RPC_URL)

# Generate or load keypair
wallet = Keypair()  # You can store/load this safely from a file or env
wallet_pubkey = wallet.public_key

# Setup logging
logging.basicConfig(level=logging.INFO)

# === Utility Functions ===
def get_sol_price():
    r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd")
    return r.json()["solana"]["usd"]

def get_wallet_balance_lamports(pubkey):
    return client.get_balance(pubkey)["result"]["value"]

def get_wallet_balance_usd():
    lamports = get_wallet_balance_lamports(wallet_pubkey)
    sol = lamports / 1e9
    price = get_sol_price()
    return sol, sol * price

def send_sol_if_ready():
    sol, usd = get_wallet_balance_usd()
    if usd >= THRESHOLD_USD:
        amount_to_send = sol - 0.001  # Leave some SOL for fees
        lamports = int(amount_to_send * 1e9)

        txn = Transaction().add(
            transfer(
                TransferParams(
                    from_pubkey=wallet.public_key,
                    to_pubkey=DEST_WALLET,
                    lamports=lamports
                )
            )
        )
        resp = client.send_transaction(txn, wallet)
        return f"✅ Payment sent! Tx: {resp['result']}"
    else:
        return fℹ️ Not enough balance. Current: ${usd:.2f}"

# === Telegram Commands ===
async def wallet_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"📬 Send SOL to:\n`{wallet_pubkey}`", parse_mode='Markdown')

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sol, usd = get_wallet_balance_usd()
    await update.message.reply_text(f"💰 Current Balance: {sol:.4f} SOL (${usd:.2f})")

async def trigger_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = send_sol_if_ready()
    await update.message.reply_text(result)

# === Bot Initialization ===
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("wallet", wallet_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("trigger", trigger_cmd))

    print(f"[BOT READY] Wallet: {wallet_pubkey}")
    app.run_polling()

if __name__ == "__main__":
    main()
