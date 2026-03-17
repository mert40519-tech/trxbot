#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Teminatlı Üye Yönetim Botu
- Sadece ADMIN_IDS listesindeki kişiler üye ekleyip silebilir
- /tadd @kullanici miktar | HİZMET  →  tek satırda ekleme
- /tlist  →  liste + her üye için t.me linki butonu
- /tsil @kullanici  →  üye sil
"""

import json
import os
import re
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════════
#  ⚙️  AYARLAR — Buraya kendi değerlerini yaz
# ════════════════════════════════════════════════════════════════════

BOT_TOKEN = "8734755865:AAGlpVZ7MwMYISDH4bogq7F8FOSV94skl38"

# Üye ekleyip silebilecek kişilerin Telegram ID'leri (int olarak)
# Kendi ID'ni öğrenmek için @userinfobot'a yaz
ADMIN_IDS = [
    7672180974,   # ← buraya kendi Telegram ID'ni yaz
    # 987654321,  # ← ikinci admin varsa ekle
]

DATA_FILE = "teminat_data.json"

# ════════════════════════════════════════════════════════════════════
#  Veri yönetimi
# ════════════════════════════════════════════════════════════════════

def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"members": {}}

def save_data(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ════════════════════════════════════════════════════════════════════
#  Yardımcı
# ════════════════════════════════════════════════════════════════════

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def parse_amount(raw: str) -> float:
    """'1.000.000$', '1,000,000', '1000000' → float"""
    cleaned = raw.replace("$", "").replace(" ", "").replace(".", "").replace(",", "")
    return float(cleaned)

def format_amount(amount: float) -> str:
    """1000000.0 → '1.000.000,00$'"""
    integer = int(amount)
    decimal = int(round((amount - integer) * 100))
    formatted = f"{integer:,}".replace(",", ".")
    return f"{formatted},{decimal:02d}$"

# ════════════════════════════════════════════════════════════════════
#  /tlist
# ════════════════════════════════════════════════════════════════════

async def tlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    members = data.get("members", {})

    if not members:
        await update.message.reply_text(
            "📋 Henüz teminatlı üye bulunmuyor.\n\n"
            "Eklemek için:\n"
            "<code>/tadd @kullanici miktar | HİZMET</code>",
            parse_mode="HTML",
        )
        return

    header = "📌 <b>Teminatlı Üyeler — TCK-158</b>\n\n"
    lines = []
    buttons = []

    for i, (username, info) in enumerate(members.items(), 1):
        amount_str = format_amount(info.get("amount", 0))
        service = info.get("service", "—").upper()
        line = f"💥 <b>TCK-158</b> | {username} | {amount_str} | {service}"
        lines.append(line)
        # Her üye için t.me butonu — tıklayınca kullanıcı profiline gider
        buttons.append([
            InlineKeyboardButton(
                f"👤 {username}",
                url=f"https://t.me/{username.lstrip('@')}"
            )
        ])

    footer = f"\n\n<i>📊 Toplam: {len(members)} teminatlı üye</i>"

    # Admin ise yönetim butonu ekle
    if is_admin(update.effective_user.id):
        buttons.append([
            InlineKeyboardButton("🗑 Üye Sil", callback_data="show_delete_list")
        ])

    await update.message.reply_text(
        header + "\n".join(lines) + footer,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )

# ════════════════════════════════════════════════════════════════════
#  /tadd  →  /tadd @kullanici miktar | HİZMET
# ════════════════════════════════════════════════════════════════════

TADD_USAGE = (
    "📝 <b>Kullanım:</b>\n"
    "<code>/tadd @kullanici miktar | HİZMET</code>\n\n"
    "<b>Örnekler:</b>\n"
    "<code>/tadd @katrehd 1.000.000 | VOİP</code>\n"
    "<code>/tadd @ahmet 5000 | VERGİ</code>\n"
    "<code>/tadd @mehmet 2500 | ESİM</code>"
)

async def tadd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("⛔ Bu komut sadece yetkili adminlere açıktır.")
        return

    raw = " ".join(context.args).strip() if context.args else ""

    if not raw:
        await update.message.reply_text(TADD_USAGE, parse_mode="HTML")
        return

    # Parse: @kullanici miktar | HİZMET
    pattern = r"^(@?\w+)\s+([\d.,]+)\s*\|\s*(.+)$"
    match = re.match(pattern, raw)

    if not match:
        await update.message.reply_text(
            "❌ Format hatalı!\n\n" + TADD_USAGE,
            parse_mode="HTML"
        )
        return

    username_raw, amount_raw, service_raw = match.groups()
    username = username_raw.lstrip("@")
    service = service_raw.strip().upper()

    try:
        amount = parse_amount(amount_raw)
    except ValueError:
        await update.message.reply_text(
            "❌ Miktar hatalı. Rakam girin: <code>1000</code> veya <code>1.000.000</code>",
            parse_mode="HTML"
        )
        return

    data = load_data()
    data["members"][username] = {
        "amount": amount,
        "service": service,
        "added_by": update.effective_user.id,
    }
    save_data(data)

    amount_str = format_amount(amount)
    await update.message.reply_text(
        f"✅ <b>Teminatlı Üye Eklendi!</b>\n\n"
        f"💥 <b>TCK-158</b> | {username} | {amount_str} | {service}\n\n"
        f"📋 Listeyi görmek için /tlist",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(
                f"👤 {username} profiline git",
                url=f"https://t.me/{username}"
            )
        ]])
    )

# ════════════════════════════════════════════════════════════════════
#  /tsil  →  /tsil @kullanici
# ════════════════════════════════════════════════════════════════════

async def tsil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("⛔ Bu komut sadece yetkili adminlere açıktır.")
        return

    if not context.args:
        await update.message.reply_text(
            "📝 <b>Kullanım:</b>\n<code>/tsil @kullanici</code>",
            parse_mode="HTML"
        )
        return

    username = context.args[0].lstrip("@")
    data = load_data()

    if username not in data["members"]:
        await update.message.reply_text(
            f"⚠️ <b>{username}</b> teminatlı üyeler listesinde bulunamadı.",
            parse_mode="HTML"
        )
        return

    del data["members"][username]
    save_data(data)

    await update.message.reply_text(
        f"🗑 <b>{username}</b> listeden silindi.\n\n📋 Güncel liste: /tlist",
        parse_mode="HTML"
    )

# ════════════════════════════════════════════════════════════════════
#  Callback: /tlist altındaki "Üye Sil" butonu
# ════════════════════════════════════════════════════════════════════

async def show_delete_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        await query.answer("⛔ Yetkiniz yok.", show_alert=True)
        return

    data = load_data()
    members = data.get("members", {})

    if not members:
        await query.message.reply_text("📋 Silinecek üye yok.")
        return

    keyboard = [
        [InlineKeyboardButton(f"🗑 {uname}", callback_data=f"delconfirm_{uname}")]
        for uname in members
    ]
    keyboard.append([InlineKeyboardButton("❌ İptal", callback_data="del_cancel")])

    await query.message.reply_text(
        "🗑 <b>Hangi üyeyi silmek istiyorsunuz?</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def confirm_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "del_cancel":
        await query.edit_message_text("❌ Silme işlemi iptal edildi.")
        return

    if not is_admin(query.from_user.id):
        await query.answer("⛔ Yetkiniz yok.", show_alert=True)
        return

    username = query.data.replace("delconfirm_", "")
    data = load_data()

    if username in data["members"]:
        del data["members"][username]
        save_data(data)
        await query.edit_message_text(
            f"✅ <b>{username}</b> listeden silindi.\n\n📋 Güncel liste: /tlist",
            parse_mode="HTML"
        )
    else:
        await query.edit_message_text("⚠️ Üye zaten listede değil.")

# ════════════════════════════════════════════════════════════════════
#  /start  /yardim
# ════════════════════════════════════════════════════════════════════

async def yardim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_note = ""
    if is_admin(update.effective_user.id):
        admin_note = (
            "\n\n🔑 <b>Admin Komutları:</b>\n"
            "<code>/tadd @kullanici miktar | HİZMET</code> — Üye ekle\n"
            "<code>/tsil @kullanici</code> — Üye sil\n\n"
            "<b>Örnek:</b>\n"
            "<code>/tadd @katrehd 1.000.000 | VOİP</code>"
        )

    await update.message.reply_text(
        "🤖 <b>Teminatlı Üye Botu</b>\n\n"
        "📋 <code>/tlist</code> — Teminatlı üye listesi\n"
        "❓ <code>/yardim</code> — Bu mesaj"
        + admin_note,
        parse_mode="HTML",
    )

# ════════════════════════════════════════════════════════════════════
#  Main
# ════════════════════════════════════════════════════════════════════

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", yardim))
    app.add_handler(CommandHandler("yardim", yardim))
    app.add_handler(CommandHandler("tlist", tlist))
    app.add_handler(CommandHandler("tadd", tadd))
    app.add_handler(CommandHandler("tsil", tsil))

    app.add_handler(CallbackQueryHandler(show_delete_list, pattern=r"^show_delete_list$"))
    app.add_handler(CallbackQueryHandler(confirm_delete_callback, pattern=r"^(delconfirm_|del_cancel)"))

    logger.info("✅ Bot başlatıldı.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

