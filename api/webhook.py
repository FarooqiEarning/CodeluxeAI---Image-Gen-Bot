import os, logging, sqlite3
from io import BytesIO
import requests
from flask import Flask, request, jsonify
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

# Load from environment
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
A4F_API_KEY = os.getenv("A4F_API_KEY")

app = Flask(__name__)

# Initialize Telegram Application
tg_app = ApplicationBuilder().token(BOT_TOKEN).build()

# SQLite setup (ephemeral storage in /tmp for Vercel)
conn = sqlite3.connect("/tmp/config.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
  CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY, value TEXT
  )
""")
conn.commit()

def get_model_id():
    cursor.execute("SELECT value FROM config WHERE key='model_id'")
    row = cursor.fetchone()
    return row[0] if row else "provider-1/FLUX.1.1-pro"

def escape_md(text: str) -> str:
    for ch in '_*[]()`~>#+=-|{}.!':
        text = text.replace(ch, f'\\{ch}')
    return text

# 🛠️ Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome! Use `/gen <prompt>` to generate images.")

async def set_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("⛔ Unauthorized.")
    if not context.args:
        return await update.message.reply_text("Usage: `/setmodel <MODEL_ID>`", parse_mode="Markdown")
    model_id = context.args[0]
    cursor.execute("REPLACE INTO config(key,value) VALUES('model_id', ?)", (model_id,))
    conn.commit()
    await update.message.reply_text(f"✅ Model set to `{model_id}`", parse_mode="Markdown")

async def get_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("⛔ Unauthorized.")
    await update.message.reply_text(f"📌 Current model: `{get_model_id()}`", parse_mode="Markdown")

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Usage: `/gen <prompt>`", parse_mode="Markdown")
    prompt = " ".join(context.args)
    await update.message.reply_text(f"🎨 Generating: `{escape_md(prompt)}`", parse_mode="MarkdownV2")
    try:
        res = requests.post(
            "https://api.a4f.co/v1/images/generations",
            headers={"Authorization": f"Bearer {A4F_API_KEY}", "Content-Type": "application/json"},
            json={"model": get_model_id(), "prompt": prompt},
            timeout=60
        )
        res.raise_for_status()
        img_url = res.json()["data"][0]["url"]
        bio = BytesIO(requests.get(img_url).content); bio.name = "img.jpg"
        await update.message.reply_photo(photo=InputFile(bio), caption="Here’s your image!")
    except Exception as e:
        logging.error(e)
        await update.message.reply_text("❌ Generation failed.")

# Register handlers
tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(CommandHandler("setmodel", set_model))
tg_app.add_handler(CommandHandler("getmodel", get_model))
tg_app.add_handler(CommandHandler("gen", generate_image))

# Webhook endpoint
@app.route("/api/webhook", methods=["POST"])
async def webhook():
    data = await request.get_json(force=True)
    update = Update.de_json(data, tg_app.bot)
    await tg_app.initialize()
    await tg_app.process_update(update)
    await tg_app.shutdown()
    return jsonify({"ok": True})

@app.route("/", methods=["GET"])
def root():
    return "Bot is live!"