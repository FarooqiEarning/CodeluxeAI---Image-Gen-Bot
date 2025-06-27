import logging
import sqlite3
import requests
from io import BytesIO
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

BOT_TOKEN = "8070910422:AAGxjNrDWvl174vY86kpw6s3xHldhJepkZY"
OWNER_ID = 8022012230
A4F_API_KEY = "ddc-a4f-1d13251bb87e4b8d9fb87359f65ac354"

# Database
conn = sqlite3.connect("user_data.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")
conn.commit()

# Helper functions
def get_model_id():
    cursor.execute("SELECT value FROM config WHERE key = 'model_id'")
    row = cursor.fetchone()
    return row[0] if row else "provider-1/FLUX.1.1-pro"

# Commands
async def set_apikey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "✨ *Usage:* `/setkey <YOUR_API_KEY>`",
            parse_mode="Markdown",
            reply_to_message_id=update.message.message_id
        )
        return
    
    api_key = context.args[0]
    chat_id = update.message.chat_id
    cursor.execute("REPLACE INTO users (chat_id, api_key) VALUES (?, ?)", (chat_id, api_key))
    conn.commit()

    try:
        await update.message.delete()
    except Exception as e:
        logging.warning(f"Failed to delete API key message: {e}")

    await update.message.chat.send_message(
        text="✅ *Your API key has been saved!*\nYou're ready to generate premium images.",
        parse_mode="Markdown"
    )

async def del_apikey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    cursor.execute("DELETE FROM users WHERE chat_id = ?", (chat_id,))
    conn.commit()
    await update.message.reply_text(
        "🗑️ *Your API key has been removed.*\nYou can set it again anytime with `/setkey <YOUR_API_KEY>`.",
        parse_mode="Markdown",
        reply_to_message_id=update.message.message_id
    )

async def set_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔ You are not authorized to use this command.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "✨ *Usage:* `/setmodel <MODEL_ID>`",
            parse_mode="Markdown",
            reply_to_message_id=update.message.message_id
        )
        return
    
    model_id = context.args[0]
    cursor.execute("REPLACE INTO config (key, value) VALUES ('model_id', ?)", (model_id,))
    conn.commit()
    await update.message.reply_text(
        f"✅ *Model ID set to:* `{model_id}`",
        parse_mode="Markdown",
        reply_to_message_id=update.message.message_id
    )

async def get_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔ You are not authorized to use this command.")
        return

    model_id = get_model_id()
    await update.message.reply_text(
        f"📌 *Current Model ID:* `{model_id}`",
        parse_mode="Markdown",
        reply_to_message_id=update.message.message_id
    )

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚡ *Provide a prompt.*\n_Example:_ `/gen A cyberpunk dragon at night`",
            parse_mode="Markdown",
            reply_to_message_id=update.message.message_id
        )
        return

    prompt = " ".join(context.args)
    model_id = get_model_id()
    username = update.effective_user.username or update.effective_user.first_name or "User"
    from datetime import datetime
    gen_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    await update.message.reply_text(
        f"🎨 *Generating image for:* `{prompt}`",
        parse_mode="Markdown",
        reply_to_message_id=update.message.message_id
    )

    url = "https://api.a4f.co/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {A4F_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model_id,
        "prompt": prompt
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()

        image_url = result['data'][0]['url']
        if not image_url:
            await update.message.reply_text(
                "❌ *No image generated.* Try a more detailed prompt.",
                parse_mode="Markdown",
                reply_to_message_id=update.message.message_id
            )
            return

        img_data = requests.get(image_url).content
        image_io = BytesIO(img_data)
        image_io.name = "spoiler_image.jpg"

        caption = (
            f"Generation Complete!*\n"
            f"👤 *Generated By:* `{username}`\n"
            f"🖼️ *Prompt:* `{prompt}`\n\n"
            f"🕒 *Time:* `{gen_time}`\n"
            "Bot created by @MuhammadGohar_Official"
        )

        await update.message.reply_photo(
            photo=InputFile(image_io),
            caption=caption,
            parse_mode="Markdown",
            has_spoiler=True,
            reply_to_message_id=update.message.message_id
        )

    except requests.exceptions.RequestException as e:
        logging.error(f"API request failed: {e}")
        await update.message.reply_text(
            "❌ *Failed to generate image.* Please try again later.",
            parse_mode="Markdown",
            reply_to_message_id=update.message.message_id
        )
    except (KeyError, IndexError):
        logging.error(f"Unexpected API response: {response.text}")
        await update.message.reply_text(
            "⚠️ *Unexpected API response.*",
            parse_mode="Markdown",
            reply_to_message_id=update.message.message_id
        )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Welcome to the Premium AI Image Bot!*\n"
        "🔑 Use `/setkey <YOUR_API_KEY>` to get started.\n"
        "🎨 Then send `/gen <your prompt>` to create amazing images.",
        parse_mode="Markdown",
        reply_to_message_id=update.message.message_id
    )

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setkey", set_apikey))
    app.add_handler(CommandHandler("delkey", del_apikey))
    app.add_handler(CommandHandler("setmodel", set_model))
    app.add_handler(CommandHandler("getmodel", get_model))
    app.add_handler(CommandHandler("gen", generate_image))

    app.run_polling()

if __name__ == "__main__":
    main()
