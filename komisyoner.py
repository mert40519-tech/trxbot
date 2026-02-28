# crypto_converter_bot.py
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Logging ayarları
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Binance API URL
BINANCE_API = "https://api.binance.com/api/v3"

class CryptoConverterBot:
    def __init__(self):
        self.symbols_cache = {}
        self.exchange_rates_cache = {}
        
    def get_all_symbols(self):
        """Binance'deki tüm işlem çiftlerini al"""
        try:
            response = requests.get(f"{BINANCE_API}/exchangeInfo", timeout=10)
            data = response.json()
            symbols = {}
            for s in data['symbols']:
                if s['status'] == 'TRADING':
                    base = s['baseAsset']
                    quote = s['quoteAsset']
                    if base not in symbols:
                        symbols[base] = []
                    symbols[base].append(quote)
            return symbols
        except Exception as e:
            logger.error(f"Sembolleri alırken hata: {e}")
            return {}

    def get_price(self, symbol):
        """Belirli bir sembolün fiyatını al"""
        try:
            response = requests.get(
                f"{BINANCE_API}/ticker/price?symbol={symbol}",
                timeout=10
            )
            data = response.json()
            return float(data['price'])
        except:
            return None

    def convert_crypto(self, amount: float, from_currency: str, to_currency: str):
        """
        Herhangi bir kripto/para birimini başka birine çevir
        """
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()
        
        # Aynı para birimi ise
        if from_currency == to_currency:
            return amount, 1.0

        # Doğrudan çift var mı kontrol et (örn: BTCUSDT)
        direct_symbol = f"{from_currency}{to_currency}"
        price = self.get_price(direct_symbol)
        
        if price:
            return amount * price, price
        
        # Ters çift var mı kontrol et (örn: USDTTRY -> TRYUSDT yerine 1/USDTTRY)
        reverse_symbol = f"{to_currency}{from_currency}"
        reverse_price = self.get_price(reverse_symbol)
        
        if reverse_price:
            rate = 1 / reverse_price
            return amount * rate, rate
        
        # USDT köprüsü kullan (örn: TRX -> TRY = TRX/USDT * USDT/TRY)
        from_usdt = self.get_price(f"{from_currency}USDT")
        to_usdt = self.get_price(f"{to_currency}USDT")
        
        if from_usdt and to_usdt:
            # from_currency -> USDT -> to_currency
            # (amount * from_usdt) / to_usdt
            rate = from_usdt / to_usdt
            return amount * rate, rate
        
        # TRY köprüsü (Türk Lirası için özel)
        if from_currency == "TRY" or to_currency == "TRY":
            usdtry = self.get_price("USDTTRY")
            if usdtry:
                if from_currency == "TRY":
                    # TRY -> USDT -> to_currency
                    usdt_amount = amount / usdtry
                    if to_currency == "USDT":
                        return usdt_amount, 1/usdtry
                    to_in_usdt = self.get_price(f"{to_currency}USDT")
                    if to_in_usdt:
                        rate = (1 / usdtry) / to_in_usdt
                        return usdt_amount / to_in_usdt, rate
                else:
                    # from_currency -> USDT -> TRY
                    from_in_usdt = self.get_price(f"{from_currency}USDT")
                    if from_in_usdt:
                        rate = from_in_usdt * usdtry
                        return amount * rate, rate
        
        return None, None

# Bot instance
converter = CryptoConverterBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot başlatma komutu"""
    welcome_message = """
🚀 *Kripto Dönüştürücü Bot'a Hoş Geldiniz!*

💱 *Desteklenen İşlemler:*
• `100 TRX TRY` - 100 TRX'i TRY'ye çevir
• `500 TRY BTC` - 500 TRY'yi BTC'ye çevir
• `1 ETH USDT` - 1 ETH'yi USDT'ye çevir
• `1000 USD TRX` - 1000 USD'yi TRX'e çevir

🌍 *Desteklenen Para Birimleri:*
• Tüm Kripto Paralar: BTC, ETH, TRX, BNB, SOL, XRP, vb.
• Stablecoinler: USDT, USDC, BUSD
• Fiat Para Birimleri: TRY, USD (USDT üzerinden)

📊 *Örnekler:*
• `100 trx to try`
• `1000 try to trx`  
• `0.5 btc usdt`
• `5000 usd eth`

💡 *Büyük/küçük harf fark etmez!*
"""
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yardım komutu"""
    help_text = """
📝 *Kullanım Kılavuzu:*

*Temel Format:*
`[MİKTAR] [KAYNAK] [HEDEF]`

*Örnekler:*
• `100 TRX TRY` → 100 TRX kaç TRY eder?
• `500 TRY BTC` → 500 TRY ile kaç BTC alınır?
• `1.5 ETH USDT` → 1.5 ETH kaç USDT eder?
• `1000 USD TRX` → 1000 USD ile kaç TRX alınır?

🔍 *Popüler Çiftler:*
• TRX ↔ TRY
• BTC ↔ USDT
• ETH ↔ USDT
• BNB ↔ USDT
• SOL ↔ USDT
• XRP ↔ USDT

⚠️ *Not:* Fiyatlar Binance borsasından gerçek zamanlı alınmaktadır.
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def convert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ana dönüştürme fonksiyonu"""
    try:
        text = update.message.text.strip().upper()
        
        # "TO" kelimesini kaldır ve ayır
        text = text.replace(" TO ", " ")
        parts = text.split()
        
        if len(parts) < 3:
            await update.message.reply_text(
                "❌ *Hatalı Format!*\n\n"
                "Doğru kullanım:\n"
                "`100 TRX TRY`\n"
                "`500 TRY BTC`\n\n"
                "Detaylı bilgi için: /help",
                parse_mode='Markdown'
            )
            return
        
        # Miktarı al (ilk kısım)
        try:
            amount = float(parts[0].replace(',', '.'))
        except ValueError:
            await update.message.reply_text(
                "❌ *Hata:* Geçerli bir miktar girin!\nÖrnek: `100 TRX TRY`",
                parse_mode='Markdown'
            )
            return
        
        from_currency = parts[1]
        to_currency = parts[2]
        
        # Dönüştürme işlemi
        result, rate = converter.convert_crypto(amount, from_currency, to_currency)
        
        if result is None:
            await update.message.reply_text(
                f"❌ *Dönüştürme Başarısız!*\n\n"
                f"`{from_currency}` → `{to_currency}` çifti bulunamadı veya hesaplanamadı.\n\n"
                f"Desteklenen para birimlerini görmek için: /help",
                parse_mode='Markdown'
            )
            return
        
        # Sonuç mesajı
        message = f"""
💱 *Dönüştürme Sonucu*

🔹 *Girdi:* `{amount:,.4f} {from_currency}`
🔹 *Çıktı:* `{result:,.8f} {to_currency}`
📊 *Kur:* `1 {from_currency} = {rate:,.8f} {to_currency}`

⏰ *Güncelleme:* Gerçek Zamanlı (Binance)
"""
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Dönüştürme hatası: {e}")
        await update.message.reply_text(
            "❌ *Bir hata oluştu!*\nLütfen tekrar deneyin.",
            parse_mode='Markdown'
        )

async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Belirli bir coinin fiyatını göster"""
    try:
        if not context.args:
            await update.message.reply_text(
                "❌ *Kullanım:* `/price BTC` veya `/price TRX`",
                parse_mode='Markdown'
            )
            return
        
        coin = context.args[0].upper()
        
        # USDT cinsinden fiyat
        price_usdt = converter.get_price(f"{coin}USDT")
        # TRY cinsinden fiyat
        usdtry = converter.get_price("USDTTRY")
        
        message = f"📊 *{coin} Fiyat Bilgisi*\n\n"
        
        if price_usdt:
            message += f"💵 *USDT:* `{price_usdt:,.4f}`\n"
            
            if usdtry:
                price_try = price_usdt * usdtry
                message += f"🇹🇷 *TRY:* `{price_try:,.2f}`\n"
        
        else:
            # TRY cinsinden direkt fiyat var mı?
            price_try_direct = converter.get_price(f"{coin}TRY")
            if price_try_direct:
                message += f"🇹🇷 *TRY:* `{price_try_direct:,.2f}`\n"
            else:
                message += "❌ Fiyat bulunamadı!"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Fiyat sorgulama hatası: {e}")
        await update.message.reply_text("❌ *Hata oluştu!*", parse_mode='Markdown')

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hata yakalama"""
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.message:
        await update.message.reply_text(
            "❌ *Bir hata oluştu!*\nLütfen komutunuzu kontrol edin.",
            parse_mode='Markdown'
        )

def main():
    """Botu başlat"""
    # TOKEN'ınızı buraya girin
    TOKEN = "8424668193:AAEDATyRHmmejUxvFv_klhV2a9xWGO1oiQ0"
    
    application = Application.builder().token(TOKEN).build()
    
    # Komutlar
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("price", price_command))
    
    # Mesaj handler - tüm metin mesajlarını dönüştürme olarak algıla
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, convert_command))
    
    # Hata handler
    application.add_error_handler(error_handler)
    
    print("🤖 Bot çalışıyor...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
	