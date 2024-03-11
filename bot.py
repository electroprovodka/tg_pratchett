from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
import csv
import os
import random
from datetime import datetime, timezone


DISABLE_THROTTLING = os.getenv("DISABLE_THROTTLING", False)
TELEGRAM_API_KEY = os.environ["TELEGRAM_API_KEY"]


QUOTES_FILE = "./quotes.csv"
DB_FILE = "./database.csv"

START_QUOTE = "Welcome, traveler! You've just turned a page into a rather unexpected chapter. Let's see where the words take us, shall we?"
MISSING_QUOTE = "It seems we've rummaged through every drawer and peeked under every magical hat, only to find that our quote vault stands empty. Fear not, for the Discworld is vast and full of tales yet untold. Give us a bit of time to refill the inkwell and bind some new pages. Check back later for more slices of wisdom and whimsy."
THROTTLING_QUOTE = "Remember, the turtle moves slowly but surely. Return on the morrow for another morsel of wisdom. Until then, good night!"

MISSING_TYPE = "missing"
THROTTLED_TYPE = "throttled"

# Format:
# id, quote
def read_quotes(filepath: str) -> dict[str, str]:
  with open(filepath, "r") as f:
    reader = csv.DictReader(f, skipinitialspace=True, quoting=csv.QUOTE_ALL)
    quotes = list(reader)
    return {q["id"]: q["quote_text"] for q in quotes}

QUOTES = read_quotes(QUOTES_FILE)

# Format:
# user_id, quote_id, viewed_at

def read_db(filepath: str) -> list[dict[str, str]]:
    if not os.path.exists(filepath):
        return []

    with open(filepath, "r") as f:
        reader = csv.DictReader(f, skipinitialspace=True, quoting=csv.QUOTE_ALL)
        db = list(reader)
        return db


def write_db(filepath: str, data: list[dict[str, str]]) -> None:
    with open(filepath, "w") as f:
        writer = csv.DictWriter(f, fieldnames=["user_id", "quote_id", "viewed_at"], skipinitialspace=True, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(data)

DB = read_db(DB_FILE)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def is_today(dt: str) -> bool:
    now = _now()
    d = datetime.fromisoformat(dt)
    return d.date() <= now.date()


def mark_as_seen(user_id: str, quote_id: str) -> None:
    DB.append({"user_id": user_id, "quote_id": quote_id, "viewed_at": _now().isoformat()})
    write_db(DB_FILE, DB)


def select_quote(user_id: str) -> str:
    all_quote_ids = set(QUOTES.keys())
    seen_ids = set([log["quote_id"] for log in DB if log["user_id"] == user_id])
    last_view = max([log["viewed_at"] for log in DB if log["user_id"] == user_id], default=None)
    if not DISABLE_THROTTLING and last_view and is_today(last_view):
        return THROTTLED_TYPE
    
    available_ids = all_quote_ids - seen_ids
    
    if not available_ids:
        return MISSING_TYPE
    return random.choice(list(available_ids))


def get_quote(user_id: str) -> str:
    quote_id = select_quote(user_id)
    if quote_id == MISSING_TYPE:
        print(f"Missing quote {user_id}")
        return MISSING_QUOTE
    elif quote_id == THROTTLED_TYPE:
        print(f"Throttled {user_id}")
        return THROTTLING_QUOTE
    
    mark_as_seen(user_id, quote_id)
    return QUOTES[quote_id]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Start {update.effective_chat.id}")
    await context.bot.send_message(chat_id=update.effective_chat.id, text=START_QUOTE)

async def new_quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Quote {update.effective_chat.id}")
    
    user_id = update.effective_chat.id
    quote_text = get_quote(str(user_id))

    await context.bot.send_message(chat_id=update.effective_chat.id, text=quote_text)


if __name__ == "__main__":
    application = ApplicationBuilder().token(TELEGRAM_API_KEY).build()

    start_handler = CommandHandler('start', start)
    quote_handler = CommandHandler('quote', new_quote)
    application.add_handler(start_handler)
    application.add_handler(quote_handler)

    application.run_polling()


# TODO: reply to random messages
# - Prerecorded quote
# - chatgpt