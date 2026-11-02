
import os
import logging

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
from yandex_music import Client

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
YANDEX_MUSIC_TOKEN = os.getenv("YANDEX_MUSIC_TOKEN")
ALLOWED_USERS = {
    int(user_id.strip())
    for user_id in os.getenv("ALLOWED_TELEGRAM_USER_IDS", "").split(",")
    if user_id.strip().isdigit()
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def authorized(update: Update) -> bool:
    user = update.effective_user
    return bool(user and (not ALLOWED_USERS or user.id in ALLOWED_USERS))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not authorized(update):
        await update.message.reply_text("Доступ запрещён.")
        return

    await update.message.reply_text(
        "🎵 Привет! Я ILSUR MUSIC AI.\n\n"
        "Команды:\n"
        "/help — помощь\n"
        "/status — проверка подключения\n"
        "/playlists — мои плейлисты\n"
        "/search запрос — поиск музыки"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not authorized(update):
        return

    await update.message.reply_text(
        "/start — запуск\n"
        "/status — статус\n"
        "/playlists — список плейлистов\n"
        "/search название — поиск треков"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not authorized(update):
        return

    if not YANDEX_MUSIC_TOKEN:
        await update.message.reply_text(
            "⚠️ Токен Яндекс Музыки ещё не добавлен."
        )
        return

    await update.message.reply_text(
        "✅ Токен Яндекс Музыки настроен.\n"
        "Проверка подключения к сервису будет выполнена при запросе."
    )


async def playlists(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not authorized(update):
        return

    if not YANDEX_MUSIC_TOKEN:
        await update.message.reply_text("Сначала добавь токен Яндекс Музыки.")
        return

    try:
        client = Client(YANDEX_MUSIC_TOKEN).init()
        account = client.account_status()
        uid = account.account.uid
        kinds = client.users_playlists_kinds(uid)
        result = client.users_playlists(uid, kinds)

        if not result:
            await update.message.reply_text("Плейлисты не найдены.")
            return

        lines = ["🎧 Твои плейлисты:"]
        for playlist in result[:30]:
            lines.append(f"• {playlist.title}")

        await update.message.reply_text("\n".join(lines))

    except Exception:
        logger.exception("Playlist request failed")
        await update.message.reply_text(
            "Не удалось загрузить плейлисты. "
            "Проверь токен и подключение."
        )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not authorized(update):
        return

    query = " ".join(context.args).strip()
    if not query:
        await update.message.reply_text("Напиши: /search название песни")
        return

    if not YANDEX_MUSIC_TOKEN:
        await update.message.reply_text("Сначала добавь токен Яндекс Музыки.")
        return

    try:
        client = Client(YANDEX_MUSIC_TOKEN).init()
        result = client.search(query, type_="track")

        tracks = result.tracks.results if result.tracks else []
        if not tracks:
            await update.message.reply_text("Ничего не найдено.")
            return

        lines = ["🔎 Результаты поиска:"]
        for track in tracks[:10]:
            artists = ", ".join(a.name for a in track.artists)
            lines.append(f"• {artists} — {track.title}")

        await update.message.reply_text("\n".join(lines))

    except Exception:
        logger.exception("Search failed")
        await update.message.reply_text("Ошибка поиска. Проверь токен.")


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("playlists", playlists))
    app.add_handler(CommandHandler("search", search))

    logger.info("ILSUR MUSIC AI started")
    app.run_polling()


if __name__ == "__main__":
    main()
