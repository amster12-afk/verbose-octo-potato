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
BOT_TOKEN = os.environ.get("BOT_TOKEN", "INSERISCI_QUI_IL_TUO_TOKEN")

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
ORDERS_PATH = os.path.join(os.path.dirname(__file__), "ordini.csv")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def load_config():
    """Rilegge il file config.json ad ogni ordine, così se lo modifichi
    non serve riavviare il bot."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# STATI DELLA CONVERSAZIONE
# ---------------------------------------------------------------------------
# Ogni numero rappresenta un "passo" della conversazione. Il ConversationHandler
# tiene traccia di dove si trova ogni utente e sa quale funzione chiamare
# quando arriva la sua prossima risposta.
NOME, PIANO, BAGNO, INTERVALLO, GIORNO, TAGLIA, QUANTITA, CONFERMA = range(8)


def build_keyboard(opzioni, prefix):
    """Crea una tastiera inline (bottoni cliccabili) a partire da una lista
    di stringhe. 'prefix' serve per riconoscere a quale domanda appartiene
    la risposta quando arriva il callback."""
    buttons = [
        [InlineKeyboardButton(testo, callback_data=f"{prefix}:{testo}")]
        for testo in opzioni
    ]
    return InlineKeyboardMarkup(buttons)


# ---------------------------------------------------------------------------
# COMANDI DI SERVIZIO
# ---------------------------------------------------------------------------
async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Restituisce il chat_id di chi scrive. Serve per configurare
    admin_chat_id in config.json la prima volta."""
    await update.message.reply_text(
        f"Il tuo chat_id è: {update.effective_chat.id}\n"
        "Copialo nel campo 'admin_chat_id' di config.json."
    )


async def annulla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Ordine annullato. Scrivi /ordina per ricominciare.")
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# FLUSSO DELL'ORDINE
# ---------------------------------------------------------------------------
async def start_ordine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Ciao! Iniziamo l'ordine della maglietta.\n\nCome ti chiami? (nome e cognome)"
    )
    return NOME


async def ricevi_nome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nome"] = update.message.text.strip()
    config = load_config()
    await update.message.reply_text(
        "In che piano ti trovi?", reply_markup=build_keyboard(config["piani"], "piano")
    )
    return PIANO


async def ricevi_piano(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    valore = query.data.split(":", 1)[1]
    context.user_data["piano"] = valore
    config = load_config()
    await query.edit_message_text(f"Piano: {valore}")
    await query.message.reply_text(
        "Quale bagno?", reply_markup=build_keyboard(config["bagni"], "bagno")
    )
    return BAGNO


async def ricevi_bagno(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    valore = query.data.split(":", 1)[1]
    context.user_data["bagno"] = valore
    config = load_config()
    await query.edit_message_text(f"Bagno: {valore}")
    await query.message.reply_text(
        "Quale intervallo?",
        reply_markup=build_keyboard(config["intervalli"], "intervallo"),
    )
    return INTERVALLO


async def ricevi_intervallo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    valore = query.data.split(":", 1)[1]
    context.user_data["intervallo"] = valore
    config = load_config()
    await query.edit_message_text(f"Intervallo: {valore}")
    await query.message.reply_text(
        "Che giorno?", reply_markup=build_keyboard(config["giorni"], "giorno")
    )
    return GIORNO


async def ricevi_giorno(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    valore = query.data.split(":", 1)[1]
    context.user_data["giorno"] = valore
    config = load_config()
    await query.edit_message_text(f"Giorno: {valore}")
    await query.message.reply_text(
        "Che taglia?", reply_markup=build_keyboard(config["taglie"], "taglia")
    )
    return TAGLIA


async def ricevi_taglia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    valore = query.data.split(":", 1)[1]
    context.user_data["taglia"] = valore
    await query.edit_message_text(f"Taglia: {valore}")
    await query.message.reply_text("Quante magliette vuoi ordinare? (scrivi un numero, es. 1)")
    return QUANTITA


async def ricevi_quantita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    testo = update.message.text.strip()

    # Validazione: deve essere un numero intero positivo. Se l'utente scrive
    # "due" o "-1" o "abc", il bot chiede di riprovare senza avanzare di stato.
    if not testo.isdigit() or int(testo) <= 0:
        await update.message.reply_text(
            "Per favore scrivi un numero intero positivo (es. 1, 2, 3)."
        )
        return QUANTITA

    quantita = int(testo)
    config = load_config()
    prezzo_unitario = config.get("prezzo_a_maglietta", 15)
    totale = quantita * prezzo_unitario

    context.user_data["quantita"] = quantita
    context.user_data["totale"] = totale

    dati = context.user_data
    riepilogo = (
        "Riepilogo ordine:\n"
        f"Nome: {dati['nome']}\n"
        f"Piano: {dati['piano']}\n"
        f"Bagno: {dati['bagno']}\n"
        f"Intervallo: {dati['intervallo']}\n"
        f"Giorno: {dati['giorno']}\n"
        f"Taglia: {dati['taglia']}\n"
        f"Quantità: {quantita}\n"
        f"Totale: {totale}€ ({prezzo_unitario}€ x {quantita})"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Conferma", callback_data="conferma:si"),
                InlineKeyboardButton("Annulla", callback_data="conferma:no"),
            ]
        ]
    )
    await update.message.reply_text(riepilogo, reply_markup=keyboard)
    return CONFERMA


async def conferma_ordine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    scelta = query.data.split(":", 1)[1]

    if scelta == "no":
        await query.edit_message_text("Ordine annullato.")
        context.user_data.clear()
        return ConversationHandler.END

    dati = context.user_data
    utente = update.effective_user

    # Salvataggio su CSV: ogni riga è un ordine. Se il file non esiste
    # ancora, scriviamo prima l'intestazione delle colonne.
    file_esiste = os.path.exists(ORDERS_PATH)
    with open(ORDERS_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_esiste:
            writer.writerow(
                ["data_ora", "username_telegram", "nome", "piano", "bagno", "intervallo",
                 "giorno", "taglia", "quantita", "totale"]
            )
        writer.writerow(
            [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                utente.username or utente.id,
                dati["nome"],
                dati["piano"],
                dati["bagno"],
                dati["intervallo"],
                dati["giorno"],
                dati["taglia"],
                dati["quantita"],
                dati["totale"],
            ]
        )

    await query.edit_message_text("Ordine registrato! Grazie.")

    # Inoltro dell'ordine all'admin: questo è il pezzo che avvisa TE su
    # Telegram ogni volta che arriva un nuovo ordine.
    config = load_config()
    admin_id = config.get("admin_chat_id", 0)
    if admin_id:
        messaggio_admin = (
            "📦 Nuovo ordine maglietta\n"
            f"Da: @{utente.username}" if utente.username else f"Da: {utente.full_name}"
        )
        messaggio_admin += (
            f"\nNome: {dati['nome']}\n"
            f"Piano: {dati['piano']}\n"
            f"Bagno: {dati['bagno']}\n"
            f"Intervallo: {dati['intervallo']}\n"
            f"Giorno: {dati['giorno']}\n"
            f"Taglia: {dati['taglia']}\n"
            f"Quantità: {dati['quantita']}\n"
            f"Totale: {dati['totale']}€"
        )
        await context.bot.send_message(chat_id=admin_id, text=messaggio_admin)
    else:
        logger.warning("admin_chat_id non configurato: nessun inoltro effettuato.")

    context.user_data.clear()
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# AVVIO DEL BOT
# ---------------------------------------------------------------------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("ordina", start_ordine)],
        states={
            NOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ricevi_nome)],
            PIANO: [CallbackQueryHandler(ricevi_piano, pattern="^piano:")],
            BAGNO: [CallbackQueryHandler(ricevi_bagno, pattern="^bagno:")],
            INTERVALLO: [CallbackQueryHandler(ricevi_intervallo, pattern="^intervallo:")],
            GIORNO: [CallbackQueryHandler(ricevi_giorno, pattern="^giorno:")],
            TAGLIA: [CallbackQueryHandler(ricevi_taglia, pattern="^taglia:")],
            QUANTITA: [MessageHandler(filters.TEXT & ~filters.COMMAND, ricevi_quantita)],
            CONFERMA: [CallbackQueryHandler(conferma_ordine, pattern="^conferma:")],
        },
        fallbacks=[CommandHandler("annulla", annulla)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("start", start_ordine))

    logger.info("Bot avviato, in ascolto...")
    app.run_polling()


if __name__ == "__main__":
    main()
