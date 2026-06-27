"""
One-time helper script to collect Telegram file_ids for your videos.

Steps:
  1. Run this script: python get_file_ids.py
  2. Open Telegram and send (or forward) each of your 5 videos to the bot one by one.
  3. The bot will reply with the file_id — copy each one into VIDEO_FILE_IDS in bot.py.
  4. Stop this script (Ctrl+C) and run bot.py as normal.
"""

import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")


async def handle_any(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message
    if not msg:
        return

    if msg.video:
        file_id = msg.video.file_id
        print(f"VIDEO — file_id: {file_id}")
        await msg.reply_text(
            f"file\\_id (copy this):\n\n`{file_id}`",
            parse_mode="Markdown",
        )
    elif msg.document:
        file_id = msg.document.file_id
        mime = msg.document.mime_type or "unknown"
        print(f"DOCUMENT ({mime}) — file_id: {file_id}")
        await msg.reply_text(
            f"file\\_id (copy this):\n\n`{file_id}`",
            parse_mode="Markdown",
        )
    elif msg.video_note:
        file_id = msg.video_note.file_id
        print(f"VIDEO NOTE — file_id: {file_id}")
        await msg.reply_text(
            f"file\\_id (copy this):\n\n`{file_id}`",
            parse_mode="Markdown",
        )
    else:
        print(f"Unknown message type received: {msg}")
        await msg.reply_text("Received something, but it's not a video. Try sending the video directly (not as a file) or as a document.")


def main() -> None:
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_any))
    print("Ready. Send each video to the bot to get its file_id. Press Ctrl+C when done.")
    app.run_polling()


if __name__ == "__main__":
    main()
