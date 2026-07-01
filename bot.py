import asyncio
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.constants import ChatAction
from telegram.error import BadRequest
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

from questions import QUESTIONS
from results import RESULTS

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Paste the file_id for each result video below (run get_file_ids.py to collect them).
VIDEO_FILE_IDS = {
    "А": "BQACAgIAAxkBAAIBdGpFNuFMVYpS73S_hyqpq_XrhP0hAAIcnwACR6sRSu451xR1UxgnPAQ",  # Потеря контакта с собой
    "Б": "BQACAgIAAxkBAAIBdmpFNxH8Kd7NVGwWsz0V38bgyfI3AAIenwACR6sRSvn0-zqnCvIePAQ",  # Страх перемен
    "В": "BQACAgIAAxkBAAIBeGpFNyISWDGbwYTnhjCinO24-XLyAAIfnwACR6sRSk-kaeNUpZeXPAQ",  # Страх проявляться
    "Г": "BQACAgIAAxkBAAIBempFNzSIo7fuYiRD1PJ04TF1RI8bAAIjnwACR6sRSh6gi4e-9mVnPAQ",  # Синдром самозванца и Стыд
    "Д": "BQACAgIAAxkBAAIBfGpFN0BVhkcjZ55SUn3xo6Xq8HXoAAIonwACR6sRSq71ruS8BqIUPAQ",  # Тревога и Самосаботаж
}

CTA_MESSAGE = (
    "ОТЛИЧНАЯ НОВОСТЬ‼️\n\n"
    "Так как вы прошли тест, у вас есть возможность попасть на коучинг со мной!\n\n"
    "Просто выполните эту анкету, и если по ответам я пойму что смогу быть вам полезной, "
    "то приглашу вас на бесплатный ознакомительный созвон."
)

CTA_LINK_MESSAGE = (
    "Переходите по ссылке, это займёт всего 5 минут ⬇️\n"
    "https://forms.gle/eA6bzwFSxdT24X1P6"
)

ANSWERING = 0

START_BUTTON_TEXT = "Начать тест ▶️"

WELCOME_MESSAGE = (
    "Сейчас ты пройдёшь небольшой тест из 10 вопросов, который поможет определить, что именно сейчас мешает твоей самореализации.\n\n"
    "Просто выбирай ответ, который ближе всего к тебе. Готова? Начнём! 👇"
)


async def typing_pause(chat_id: int, bot, seconds: float = 3) -> None:
    await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    await asyncio.sleep(seconds)


def build_keyboard(question_index: int) -> InlineKeyboardMarkup:
    options = QUESTIONS[question_index]["options"]
    keyboard = [
        [InlineKeyboardButton(f"{letter} — {text}", callback_data=letter)]
        for letter, text in options
    ]
    return InlineKeyboardMarkup(keyboard)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    keyboard = ReplyKeyboardMarkup(
        [[START_BUTTON_TEXT]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await update.message.reply_text(
        "Привет! 👋 Нажми кнопку ниже, чтобы начать тест 👇",
        reply_markup=keyboard,
    )
    return ConversationHandler.END


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["question_index"] = 0
    context.user_data["answers"] = []

    await update.message.reply_text(WELCOME_MESSAGE, reply_markup=ReplyKeyboardRemove())
    await typing_pause(update.effective_chat.id, context.bot, seconds=3)
    await update.message.reply_text(
        QUESTIONS[0]["text"],
        reply_markup=build_keyboard(0),
    )
    return ANSWERING


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    letter = query.data
    answers: list = context.user_data.setdefault("answers", [])
    answers.append(letter)

    current_index: int = context.user_data.get("question_index", 0)
    answer_text = dict(QUESTIONS[current_index]["options"]).get(letter, letter)

    # Lock in the answered question — removes keyboard so past questions can't be re-clicked.
    # If edit fails, this callback was already processed (duplicate delivery), so skip.
    try:
        await query.message.edit_text(
            f"{QUESTIONS[current_index]['text']}\n\n✅ {letter} — {answer_text}"
        )
    except BadRequest:
        await query.answer()
        return ANSWERING

    question_index = current_index + 1
    context.user_data["question_index"] = question_index

    if question_index < len(QUESTIONS):
        await query.message.reply_text(
            QUESTIONS[question_index]["text"],
            reply_markup=build_keyboard(question_index),
        )
        return ANSWERING

    # All questions answered — compute result
    counts = {l: answers.count(l) for l in "АБВГД"}
    result_letter = max(counts, key=lambda l: (counts[l], -"АБВГД".index(l)))
    # tie-break: highest count wins; among ties, first alphabetically (А < Б < В < Г < Д)
    result_letter = max(
        counts,
        key=lambda l: (counts[l], -list("АБВГД").index(l)),
    )
    result_name = RESULTS[result_letter]

    user_id = update.effective_user.id
    print(f"User {user_id} completed quiz. Result: {result_letter} — {result_name}")

    await typing_pause(query.message.chat_id, context.bot, seconds=2)
    await query.message.reply_text("Анализируем твои ответы...")

    await typing_pause(query.message.chat_id, context.bot, seconds=3)
    await query.message.reply_text("Формируем финальный результат ⏳")

    await typing_pause(query.message.chat_id, context.bot, seconds=2)
    await query.message.reply_text("Твой результат готов! 🎯")

    video_file_id = VIDEO_FILE_IDS.get(result_letter)
    if video_file_id:
        await context.bot.send_video(
            chat_id=query.message.chat_id,
            video=video_file_id,
        )
    else:
        print(f"No video file_id set for result letter: {result_letter}")
        await query.message.reply_text(f"Твой результат: {result_name}")

    await asyncio.sleep(10)
    await query.message.reply_text(CTA_MESSAGE)

    await asyncio.sleep(3)
    restart_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Пройти ещё раз", callback_data="restart")]
    ])
    await query.message.reply_text(CTA_LINK_MESSAGE, reply_markup=restart_keyboard)
    return ConversationHandler.END


async def handle_restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    context.user_data["question_index"] = 0
    context.user_data["answers"] = []

    await query.message.reply_text(WELCOME_MESSAGE)
    await query.message.reply_text(
        QUESTIONS[0]["text"],
        reply_markup=build_keyboard(0),
    )
    return ANSWERING


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Пожалуйста, выбери ответ с помощью кнопок выше 👆"
    )
    return ANSWERING


def main() -> None:
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", cmd_start),
            MessageHandler(filters.Text([START_BUTTON_TEXT]), start),
            CallbackQueryHandler(handle_restart, pattern="^restart$"),
        ],
        states={
            ANSWERING: [
                CallbackQueryHandler(handle_answer, pattern="^[АБВГД]$"),
                CallbackQueryHandler(
                    lambda u, c: u.callback_query.answer(),
                    pattern="^restart$",
                ),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text),
            ],
        },
        fallbacks=[CommandHandler("start", cmd_start)],
        allow_reentry=True,
    )

    app.add_handler(conv_handler)

    print("Bot is running. Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
