import re
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters,
)

# ─── AYARLAR ────────────────────────────────────────────────
BOT_TOKEN = "8734755865:AAGxtRIovW_RL3D2YtZiJpxfOoLTeIASIOQ"

# @ linklerini de sil? (True = sil, False = sadece t.me linklerini sil)
REMOVE_AT_LINKS = True

# Sadece bu grup ID'lerinde çalışsın (boş bırakırsan tüm gruplarda çalışır)
# Örnek: ALLOWED_GROUPS = [-1001234567890, -1009876543210]
ALLOWED_GROUPS = []
# ────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Silinecek link pattern'ları
LINK_PATTERNS = [
    r'https?://t\.me/joinchat/[^\s,،؛;\'")\]}>]+',
    r'https?://t\.me/\+[^\s,،؛;\'")\]}>]+',
    r'https?://t\.me/[a-zA-Z][a-zA-Z0-9_]{3,}(?:/\d+)?',
    r'https?://telegram\.me/[^\s,،؛;\'")\]}>]+',
    r'https?://telegram\.dog/[^\s,،؛;\'")\]}>]+',
]

AT_PATTERN = r'@[a-zA-Z][a-zA-Z0-9_]{3,}'

COMBINED_PATTERN = re.compile(
    '|'.join(LINK_PATTERNS) + (f'|{AT_PATTERN}' if REMOVE_AT_LINKS else ''),
    re.IGNORECASE
)


def contains_link(text: str) -> bool:
    """Metinde Telegram linki var mı kontrol et."""
    return bool(COMBINED_PATTERN.search(text))


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message or update.edited_message
    if not message:
        return

    # Grup kontrolü
    if ALLOWED_GROUPS and message.chat.id not in ALLOWED_GROUPS:
        return

    # Sadece gruplarda çalış
    if message.chat.type not in ("group", "supergroup"):
        return

    text = message.text or message.caption or ""
    if not text:
        return

    if not contains_link(text):
        return

    try:
        await message.delete()
        logger.info(
            f"Silindi | Grup: {message.chat.title} ({message.chat.id}) "
            f"| Kullanıcı: {message.from_user.username or message.from_user.first_name} "
            f"| Mesaj: {text[:80]}"
        )
    except Exception as e:
        logger.warning(f"Mesaj silinemedi: {e}")


def main():
    print("Bot başlatılıyor...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Hem normal hem düzenlenen mesajları yakala
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, handle_message))

    print("Bot çalışıyor. Durdurmak için CTRL+C")
    app.run_polling()


if __name__ == "__main__":
    main()
