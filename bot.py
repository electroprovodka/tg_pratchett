from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, ContextTypes, CommandHandler
import csv
import os
import random
from datetime import datetime, timezone
import logging


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

DISABLE_THROTTLING = os.getenv("DISABLE_THROTTLING", False)
TELEGRAM_API_KEY = os.environ["TELEGRAM_API_KEY"]


QUOTES_FILE = "./quotes.csv"
DB_FILE = "./database.csv"

START_QUOTE = "Welcome, traveler! You've just turned a page into a rather unexpected chapter. Let's see where the words take us, shall we?"
MISSING_QUOTES = [
    "It seems we've rummaged through every drawer and peeked under every magical hat, only to find that our quote vault stands empty. Fear not, for the Discworld is vast and full of tales yet untold. Give us a bit of time to refill the inkwell and bind some new pages. Check back later for more slices of wisdom and whimsy.",
]
THROTTLING_QUOTE = [
    "Remember, the turtle moves slowly but surely. Return on the morrow for another morsel of wisdom. Until then, good night!",
        "The sands of our hourglass have run low for today. Swing by on the morrow for another gem!",
    "Every tale needs a pause. Return with the dawn for your next chapter of wisdom.",
    "The stars say it's time to rest. A fresh quote awaits with the morning light.",
    "As the Disc rests, so shall our quest for quotes. Tomorrow, the adventure continues!",
]

RANDOM_RESPONSES = [
    "Ah, it seems my Luggage has wandered off with that understanding. Could you charm me with a /quote command instead, just until it returns?",
    "Your spell has tickled my curiosity, but my magical interpreter is out sipping tea. Perhaps a /quote command might clear the mist?",
    "I've wandered into a curious dimension where your words puzzle me. Could we navigate back with a /quote command, just to ensure we're on the same page?",
]

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
    return now.date() == d.date()


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
        logger.warning(f"Missing quote {user_id}")
        return random.choice(MISSING_QUOTES)
    elif quote_id == THROTTLED_TYPE:
        logger.info(f"Throttled {user_id}")
        return random.choice(THROTTLING_QUOTE)
    
    mark_as_seen(user_id, quote_id)
    return QUOTES[quote_id]



async def send(context: ContextTypes.DEFAULT_TYPE, chat_id: str, text: str) -> None:
    # Retry 3 times
    for _ in range(3):
        try:
            await context.bot.send_message(chat_id=chat_id, text=text)
            break
        except Exception as e:
            logger.error(f"Error {e}")
            continue


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Start {update.effective_chat.id}")
    await send(context, chat_id=update.effective_chat.id, text=START_QUOTE)

async def new_quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Quote {update.effective_chat.id}")
    
    user_id = update.effective_chat.id
    quote_text = get_quote(str(user_id))

    await send(context, chat_id=update.effective_chat.id, text=quote_text)


async def random_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply = random.choice(RANDOM_RESPONSES)
    await send(context, chat_id=update.effective_chat.id, text=reply)


if __name__ == "__main__":
    logger.info("Starting...")
    application = ApplicationBuilder().token(TELEGRAM_API_KEY).build()

    start_handler = CommandHandler('start', start)
    quote_handler = CommandHandler('quote', new_quote)
    random_message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), random_message)

    application.add_handler(start_handler)
    application.add_handler(quote_handler)
    application.add_handler(random_message_handler)

    application.run_polling()
