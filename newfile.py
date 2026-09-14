import json
import csv
import logging
import os
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ---------------------------------------------------------------------------
# CONFIGURAZIONE
# ---------------------------------------------------------------------------
# Il token si prende da @BotFather su Telegram (comando /newbot).
# Non scriverlo mai direttamente nel codice se condividi il file: qui lo
# leggiamo da una variabile d'ambiente, con un valore di fallback per test.
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8717687295:AAGshJz7OUBeSAiG1Z7fr2n7jwtwMCL2A0c")

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
ORDERS_PATH = os.path.join(os.path.dirname(__file__), "ordini.csv")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

