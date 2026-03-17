#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Teminatlı Üye Botu — SS'deki bota birebir benzer görünüm
/tlist → Yeşil inline buton listesi (💥kullanici | miktar | hizmet)
/tadd @kullanici [serbest metin] → Admin üye ekler
/tsil @kullanici → Admin üye siler
"""

import json, os, logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════
#  AYARLAR
# ═══════════════════════════════════════════

BOT_TOKEN  = "8734755865:AAGlpVZ7MwMYISDH4bogq7F8FOSV94skl38"   # @BotFather'dan al

ADMIN_IDS  = [
    7672180974,    # ← kendi Telegram ID'n (@userinfobot ile öğren)
    # 987654321,  # ikinci admin
]

DATA_FILE  = "teminat_data.json"
PAGE_SIZE  = 5   # bir sayfada kaç buton

# ═══════════════════════════════════════════
#  Veri
# ═══════════════════════════════════════════

def load() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"members": {}, "order": []}

def save(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS

# ═══════════════════════════════════════════
#  Buton metnini oluştur — SS formatı:
#  💥kullanici | bilgi
# ═══════════════════════════════════════════

def btn_label(username: str, info: str) -> str:
    return f"💥{username} | {info}"

# ═══════════════════════════════════════════
#  Sayfalama yardımcısı
# ═══════════════════════════════════════════

def build_keyboard(members: dict, order: list, page: int, uid: int):
    """
    Her üye → yeşil inline buton (t.me linki).
    Alt satır: ← Geri | Başa Dön | İleri →
    Admin ise ayrıca: ➕ Üye Ekle | 🗑 Üye Sil
    """
    keys = [u for u in order if u in members]
    total_pages = max(1, (len(keys) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))

    chunk = keys[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]

    rows = []
    for uname in chunk:
        info = members[uname].get("info", "")
        rows.append([InlineKeyboardButton(
            text=btn_label(uname, info),
            url=f"https://t.me/{uname}"
        )])

    # Sayfalama satırı
    nav = []
    if total_pages > 1:
        nav.append(InlineKeyboardButton("⬅️ Geri",     callback_data=f"page_{page-1}" if page > 0 else "noop"))
        nav.append(InlineKeyboardButton("🏠 Başa Dön", callback_data="page_0"))
        nav.append(InlineKeyboardButton("İleri ➡️",    callback_data=f"page_{page+1}" if page < total_pages-1 else "noop"))
        rows.append(nav)



    return InlineKeyboardMarkup(rows), page, total_pages

def build_header(page: int, total_pages: int, total: int) -> str:
    return (
        f"📌 <b>Teminatlı TCK-158 Üyeleri</b>\n"
        f"Sayfa {page+1}/{total_pages}\n\n"
        f"• Butonlar → Kullanıcı profiline yönlendirir\n\n"
        f"<i>Toplam: {total} teminatlı üye</i>"
    )

# ═══════════════════════════════════════════
#  /tlist
# ═══════════════════════════════════════════

async def tlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load()
    members = data.get("members", {})
    order   = data.get("order", list(members.keys()))

    if not members:
        await update.message.reply_text(
            "📋 Henüz teminatlı üye yok.\n\n",
            parse_mode="HTML"
        )
        return

    kbd, page, total_pages = build_keyboard(members, order, 0, update.effective_user.id)
    await update.message.reply_text(
        build_header(page, total_pages, len(members)),
        parse_mode="HTML",
        reply_markup=kbd,
    )

# ═══════════════════════════════════════════
#  Sayfa callback
# ═══════════════════════════════════════════

async def page_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "noop":
        return

    page = int(query.data.split("_")[1])
    data = load()
    members = data.get("members", {})
    order   = data.get("order", list(members.keys()))

    kbd, page, total_pages = build_keyboard(members, order, page, query.from_user.id)
    await query.edit_message_text(
        build_header(page, total_pages, len(members)),
        parse_mode="HTML",
        reply_markup=kbd,
    )

# ═══════════════════════════════════════════
#  /tadd @kullanici [serbest bilgi]
#
#  Admin istediği her şeyi yazabilir:
#  /tadd @katrehd 1.000.000$ | VOİP
#  /tadd @ahmet vergi 5000
#  /tadd @mehmet ESİM teminatlı güvenilir
# ═══════════════════════════════════════════

async def tadd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text("⛔ Bu komut sadece yetkili adminlere açıktır.")
        return

    args = context.args  # liste
    if not args or not args[0].startswith("@"):
        await update.message.reply_text(
            "📝 <b>Kullanım:</b>\n"
            "<code>/tadd @kullanici bilgi</code>\n\n"
            "<b>Örnekler:</b>\n"
            "<code>/tadd @katrehd 1.000.000$ | VOİP</code>\n"
            "<code>/tadd @ahmet 5.000$ | VERGİ</code>\n"
            "<code>/tadd @mehmet 2.500$ | ESİM</code>",
            parse_mode="HTML"
        )
        return

    username = args[0].lstrip("@")
    # @kullanici'dan sonra gelen her şey "bilgi" olarak alınır
    info = " ".join(args[1:]).strip() if len(args) > 1 else ""

    data = load()
    if "order" not in data:
        data["order"] = list(data.get("members", {}).keys())

    data["members"][username] = {"info": info, "added_by": uid}
    if username not in data["order"]:
        data["order"].append(username)
    save(data)

    label = btn_label(username, info)
    await update.message.reply_text(
        f"✅ <b>Teminatlı üye eklendi!</b>\n\n"
        f"{label}\n\n"
        f"📋 Liste: /tlist",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(f"👤 {username}", url=f"https://t.me/{username}")
        ]])
    )

# ═══════════════════════════════════════════
#  /tsil @kullanici
# ═══════════════════════════════════════════

async def tsil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text("⛔ Bu komut sadece yetkili adminlere açıktır.")
        return

    if not context.args:
        await update.message.reply_text(
            "📝 <b>Kullanım:</b> <code>/tsil @kullanici</code>",
            parse_mode="HTML"
        )
        return

    username = context.args[0].lstrip("@")
    data = load()

    if username not in data.get("members", {}):
        await update.message.reply_text(f"⚠️ <b>{username}</b> listede bulunamadı.", parse_mode="HTML")
        return

    del data["members"][username]
    if username in data.get("order", []):
        data["order"].remove(username)
    save(data)

    await update.message.reply_text(
        f"🗑 <b>{username}</b> listeden silindi.\n📋 Güncel liste: /tlist",
        parse_mode="HTML"
    )

# ═══════════════════════════════════════════
#  Admin callback butonları (tlist içinden)
# ═══════════════════════════════════════════

async def admin_add_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        await query.answer("⛔ Yetkiniz yok.", show_alert=True)
        return
    await query.message.reply_text(
        "➕ <b>Üye eklemek için:</b>\n\n"
        "<code>/tadd @kullanici bilgi</code>\n\n"
        "<b>Örnekler:</b>\n"
        "<code>/tadd @katrehd 1.000.000$ | VOİP</code>\n"
        "<code>/tadd @ahmet 5.000$ | VERGİ</code>",
        parse_mode="HTML"
    )

async def admin_del_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        await query.answer("⛔ Yetkiniz yok.", show_alert=True)
        return

    data = load()
    members = data.get("members", {})
    order   = data.get("order", list(members.keys()))
    keys    = [u for u in order if u in members]

    if not keys:
        await query.message.reply_text("📋 Silinecek üye yok.")
        return

    keyboard = [[InlineKeyboardButton(f"🗑 {u}", callback_data=f"deldo_{u}")] for u in keys]
    keyboard.append([InlineKeyboardButton("❌ İptal", callback_data="del_cancel")])

    await query.message.reply_text(
        "🗑 <b>Hangi üyeyi silmek istiyorsunuz?</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def deldo_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "del_cancel":
        await query.edit_message_text("❌ İptal edildi.")
        return

    if not is_admin(query.from_user.id):
        await query.answer("⛔ Yetkiniz yok.", show_alert=True)
        return

    username = query.data.replace("deldo_", "")
    data = load()

    if username in data.get("members", {}):
        del data["members"][username]
        if username in data.get("order", []):
            data["order"].remove(username)
        save(data)
        await query.edit_message_text(
            f"✅ <b>{username}</b> silindi.\n📋 Güncel liste: /tlist",
            parse_mode="HTML"
        )
    else:
        await query.edit_message_text("⚠️ Üye zaten listede değil.")

# ═══════════════════════════════════════════
#  /start /yardim
# ═══════════════════════════════════════════


# ═══════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",  yardim))
    app.add_handler(CommandHandler("yardim", yardim))
    app.add_handler(CommandHandler("tlist",  tlist))
    app.add_handler(CommandHandler("tadd",   tadd))
    app.add_handler(CommandHandler("tsil",   tsil))

    app.add_handler(CallbackQueryHandler(page_cb,        pattern=r"^page_\d+$"))
    app.add_handler(CallbackQueryHandler(page_cb,        pattern=r"^noop$"))
    app.add_handler(CallbackQueryHandler(admin_add_help, pattern=r"^admin_add_help$"))
    app.add_handler(CallbackQueryHandler(admin_del_list, pattern=r"^admin_del_list$"))
    app.add_handler(CallbackQueryHandler(deldo_cb,       pattern=r"^(deldo_|del_cancel)"))

    logger.info("✅ Bot başlatıldı.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
