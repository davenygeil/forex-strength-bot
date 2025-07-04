import asyncio
import aiohttp
import os
from telegram import Bot
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# === CONFIG ===
API_KEY = os.getenv("TWELVE_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = Bot(token=TELEGRAM_BOT_TOKEN)

CURRENCY_PAIRS = [
    "EUR/USD", "USD/JPY", "GBP/USD", "AUD/USD", "USD/CAD", "NZD/USD",
    "EUR/JPY", "EUR/GBP", "EUR/AUD", "EUR/NZD", "GBP/JPY", "AUD/JPY", "USD/MXN"
]

CURRENCIES = ["USD", "EUR", "JPY", "GBP", "AUD", "CAD", "NZD", "MXN"]
EXCLUDED = ["CHF"]

# === HELPER FUNCTIONS ===
async def fetch_candle(session, symbol):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1h&outputsize=2&apikey={API_KEY}"
    async with session.get(url) as response:
        data = await response.json()
        return symbol, data

def analyze_candles(candle_data):
    strength = {cur: 0 for cur in CURRENCIES if cur not in EXCLUDED}

    for symbol, data in candle_data:
        if data.get("status") == "error":
            continue
        try:
            values = data["values"]
            if len(values) < 2:
                continue
            current = values[0]
            open_price = float(current["open"])
            close_price = float(current["close"])

            left, right = symbol.split("/")
            if left in EXCLUDED or right in EXCLUDED:
                continue

            if close_price > open_price:
                strength[left] += 1
                strength[right] -= 1
            elif close_price < open_price:
                strength[left] -= 1
                strength[right] += 1
        except Exception:
            continue
    return strength

def format_strength_output(scores):
    return "\n".join([f"{cur}: {score}" for cur, score in scores.items()])

# === MAIN TASK ===
async def analyze_and_send():
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_candle(session, pair.replace("/", "")) for pair in CURRENCY_PAIRS]
        results = await asyncio.gather(*tasks)
        scores = analyze_candles(results)
        message = f"📊 1H Candle Strength (Updated {datetime.utcnow().strftime('%H:%M')} UTC):\n\n"
        message += format_strength_output(scores)
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)

async def wait_until_next_hour():
    now = datetime.utcnow()
    next_hour = (now + timedelta(hours=1)).replace(minute=0, second=10, microsecond=0)
    wait_seconds = (next_hour - now).total_seconds()
    print(f"⏳ Waiting {int(wait_seconds)} seconds until next candle close...")
    await asyncio.sleep(wait_seconds)

async def job_loop():
    while True:
        await wait_until_next_hour()
        await analyze_and_send()

if __name__ == "__main__":
    asyncio.run(job_loop())
