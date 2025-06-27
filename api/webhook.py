import os
import logging
import sqlite3
from io import BytesIO
import requests
from fastapi import FastAPI, Request, Response
from telegram import Update, InputFile, Bot
from telegram.ext import Dispatcher, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
A4F_API_KEY = os.getenv("A4F_API_KEY")

# Set up DB
conn = sqlite3.connect("/tmp/config.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")
conn.commit()

def get_model_id():
    cursor.execute("SELECT value FROM config WHERE key = 'model_id'")
    row = cursor.fetchone()
    return row[0] if row else "provider-1/FLUX.1.1-pro"

def escape_md(text: str) -> str:
    for ch in '_*[]()`~>#+=-|{}.!':
        text = text.replace(ch, f'\\{ch}')
    return text

# Command handlers (same logic)
async def set_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔ Unauthorized.")
        return
    if not context.args:
        await update.message.reply_text("Usage: `/setmodel <MODEL_ID>`", parse_mode="Markdown")
        return
    model_id = context.args[0]
    cursor.execute("REPLACE INTO config (key, value) VALUES ('model_id', ?)", (model_id,))
    conn.commit()
    await update.message.reply_text(f"✅ Model set to `{model_id}`", parse_mode="Markdown")

async def get_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔ Unauthorized.")
        return
    await update.message.reply_text(f"📌 Current model: `{get_model_id()}`", parse_mode="Markdown")

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: `/gen <prompt>`", parse_mode="Markdown")
        return
    prompt = " ".join(context.args)
    await update.message.reply_text(f"🎨 Generating: `{escape_md(prompt)}`", parse_mode="MarkdownV2")

    try:
        res = requests.post(
            "https://api.a4f.co/v1/images/generations",
            headers={
                "Authorization": f"Bearer {A4F_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"model": get_model_id(), "prompt": prompt},
            timeout=60
        )
        res.raise_for_status()
        img_url = res.json()["data"][0]["url"]
        img_data = requests.get(img_url).content
        bio = BytesIO(img_data); bio.name="img.jpg"
        await update.message.reply_photo(photo=InputFile(bio), caption=f"Here’s your image!", reply_to_message_id=update.message.message_id)
    except Exception as e:
        logging.error(e)
        await update.message.reply_text("❌ Generation failed.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome! Use `/gen <prompt>`.")

# Setup FastAPI app + webhook route
app = FastAPI()
bot = Bot(BOT_TOKEN)
dp = Dispatcher(bot, None, workers=1, use_context=True)
dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("setmodel", set_model))
dp.add_handler(CommandHandler("getmodel", get_model))
dp.add_handler(CommandHandler("gen", generate_image))

@app.post("/api/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot)
    dp.process_update(update)
    return Response(status_code=200)

@app.get("/")
def read_root():
    return {"status": "ok"}
