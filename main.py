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

# Sadece bu grup ID'lerinde çalışsın (boş bırakırsan tüm gruplarda çalışır)
# Örnek: ALLOWED_GROUPS = [-1001234567890, -1009876543210]
ALLOWED_GROUPS = []
# ────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Sadece t.me URL formatındaki linkleri yakala (@ kullanıcı adlarına dokunma)
URL_PATTERN = re.compile(
    r'https?://(t\.me|telegram\.me|telegram\.dog)/[^\s,،؛;\'")\]}>]+',
    re.IGNORECASE
)


def contains_telegram_link(text: str, entities: list) -> bool:
    """
    Mesajda Telegram kanal/grup linki var mı kontrol et.
    - t.me/... URL'leri → yakala
    - Telegram'ın kendi 'mention' entity'si (@kullaniciadi) → yoksay (kullanıcı adı)
    - Telegram'ın 'url' entity'si içinde t.me geçiyorsa → yakala
    """
    # URL pattern ile düz metin kontrolü
    if URL_PATTERN.search(text):
        return True

    # Telegram entity'leri üzerinden kontrol (inline linkler vb.)
    if entities:
        for entity in entities:
            # 'mention' tipi = @kullaniciadi → kullanıcı adı, dokunma
            if entity.type == "mention":
                continue
            # 'url' veya 'text_link' ise ve t.me içeriyorsa → sil
            if entity.type == "url":
                start = entity.offset
                end = entity.offset + entity.length
                url_text = text[start:end]
                if re.search(r'(t\.me|telegram\.me|telegram\.dog)', url_text, re.IGNORECASE):
                    return True
            if entity.type == "text_link" and entity.url:
                if re.search(r'(t\.me|telegram\.me|telegram\.dog)', entity.url, re.IGNORECASE):
                    return True

    return False


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

    entities = message.entities or message.caption_entities or []
    if not contains_telegram_link(text, entities):
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
