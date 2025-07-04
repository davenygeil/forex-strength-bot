import asyncio
import aiohttp
from collections import defaultdict
from telegram import Bot
import datetime

# === YOUR KEYS (Hardcoded for testing; move to .env later for security) ===
TWELVE_API_KEY = "a7015e4ff7334de8b2cbbd885372ad2d"
TELEGRAM_BOT_TOKEN = "7553675707:AAFrct9sDFIcvzujJiaSBfzAc5yqKbKxqhw"
TELEGRAM_CHAT_ID = 6252832783  # No quotes for int

# === Forex Pairs Using Twelve Data Format (with :FX) ===
PAIRS = [
    "EUR/USD:FX",
    "USD/JPY:FX",
    "GBP/USD:FX",
    "AUD/USD:FX",
    "USD/CAD:FX",
    "NZD/USD:FX"
]

async def fetch_candle(session, symbol):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1h&apikey={TWELVE_API_KEY}&outputsize=2"
    async with session.get(url) as response:
        data = await response.json()
        print(f"DEBUG: {symbol} response: {data}")

        if "values" not in data:
            return symbol, None

        try:
            candles = data['values']
            open_price = float(candles[1]['open'])
            close_price = float(candles[1]['close'])
            return symbol, close_price > open_price
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            return symbol, None

async def analyze_pairs():
    score = defaultdict(int)
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_candle(session, symbol) for symbol in PAIRS]
        results = await asyncio.gather(*tasks)
        for symbol, is_bullish in results:
            if is_bullish is None:
                continue
            base = symbol[:3]
            quote = symbol[4:7]
            if is_bullish:
                score[base] += 1
                score[quote] -= 1
            else:
                score[base] -= 1
                score[quote] += 1
    return score

async def send_to_telegram(score):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    message = f"📊 Currency Strength - {timestamp} (UTC)\n\n"
    message += "\n".join([f"{k}: {v}" for k, v in sorted(score.items())])
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)

async def job_loop():
    while True:
        now = datetime.datetime.utcnow()
        # Schedule to run 5 seconds after the top of the hour
        next_hour = (now + datetime.timedelta(hours=1)).replace(minute=0, second=5, microsecond=0)
        wait_seconds = (next_hour - now).total_seconds()
        
        print(f"⏳ Waiting {int(wait_seconds)} seconds until next candle close at {next_hour.strftime('%H:%M:%S')} UTC...")
        await asyncio.sleep(wait_seconds)

        try:
            print("📡 Analyzing candle data...")
            score = await analyze_pairs()
            await send_to_telegram(score)
            print(f"✅ Signal sent at {datetime.datetime.utcnow().strftime('%H:%M:%S')} UTC\n")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(job_loop())
