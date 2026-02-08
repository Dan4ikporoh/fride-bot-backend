import sqlite3
import json
import asyncio
import sys
import random
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- НАСТРОЙКИ ---
BOT_TOKEN = '8427909250:AAEZeoXeDG7fbhfczxrVyqtY6xB6g6SOhdo' # Твой токен
ADMIN_ID = 8307741307 # Твой ID (цифрами)
ADMIN_USERNAME = '@Dead_Hard11'
GAME_URL = "https://dan4ikporoh.github.io/F-Game/"

DB_NAME = 'fride_rpg.db'

# Кнопки
BTN_GAME = "🎮 ИГРАТЬ"
BTN_GET_PROMO = "🎁 Получить код"
BTN_WITHDRAW = "💸 Вывод средств"
BTN_SUPPORT = "🆘 Поддержка"

def init_db():
    with sqlite3.connect(DB_NAME) as con:
        cur = con.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0, bottles INTEGER DEFAULT 0, record INTEGER DEFAULT 0)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS used_promos (user_id INTEGER, promo TEXT)''')
        con.commit()

def get_data(user_id):
    with sqlite3.connect(DB_NAME) as con:
        cur = con.cursor()
        cur.execute("SELECT balance, bottles, record FROM users WHERE user_id = ?", (user_id,))
        res = cur.fetchone()
        if res: return res
        cur.execute("INSERT INTO users (user_id, balance, bottles, record) VALUES (?, 0, 0, 0)", (user_id,))
        con.commit()
        return (0, 0, 0)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bal, bot, rec = get_data(user_id)
    
    # Ссылка
    url = f"{GAME_URL}?balance={bal}&bottles={bot}&record={rec}"
    
    # ВАЖНО: Кнопка ИГРАТЬ теперь внизу! Только так работает отправка данных.
    kb = [
        [KeyboardButton(text=BTN_GAME, web_app=WebAppInfo(url=url))],
        [KeyboardButton(text=BTN_WITHDRAW), KeyboardButton(text=BTN_GET_PROMO)],
        [KeyboardButton(text=BTN_SUPPORT)]
    ]
    
    await update.message.reply_text(
        f"🌌 <b>FRIDE NEON</b>\n💰 Баланс: {bal} руб.\n🏆 Рекорд: {rec} м.\n\n"
        "👇 Жми большую кнопку <b>ИГРАТЬ</b> внизу экрана!",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
        parse_mode='HTML'
    )

async def data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Лог в терминал, чтобы ты видел, что процесс пошел
    print("📩 ПРИШЛИ ДАННЫЕ ИЗ ИГРЫ!") 
    try:
        data = json.loads(update.effective_message.web_app_data.data)
        uid = update.effective_user.id
        
        if data.get("action") == "withdraw":
            print("💸 Заявка на вывод!")
            amount = int(data["amount"])
            
            # Списываем
            with sqlite3.connect(DB_NAME) as con:
                con.cursor().execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, uid))
                con.commit()
            
            # Отправляем админу
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_ID, 
                    text=f"🚨 <b>ВЫВОД!</b>\n👤 Игрок: @{update.effective_user.username}\n📝 Ник: {data['char_name']}\n💰 Сумма: {amount} руб.",
                    parse_mode='HTML'
                )
                print("✅ Сообщение ушло админу")
            except Exception as e:
                print(f"❌ Ошибка отправки админу: {e}")
                
            await update.message.reply_text("✅ Заявка отправлена!")

        elif data.get("action") == "save":
            with sqlite3.connect(DB_NAME) as con:
                con.cursor().execute("UPDATE users SET balance=?, bottles=?, record=? WHERE user_id=?", 
                    (int(data["balance"]), int(data["bottles"]), int(data["record"]), uid))
                con.commit()
            await update.message.reply_text("💾 Сохранено!")
            
    except Exception as e:
        print(f"Ошибка в коде: {e}")

async def promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    txt = update.message.text
    codes = {"OpenFride": 50000, "FrideRolePlay": 100000}
    
    if txt in codes:
        with sqlite3.connect(DB_NAME) as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM used_promos WHERE user_id=? AND promo=?", (uid, txt))
            if cur.fetchone():
                await update.message.reply_text("❌ Уже использован!")
            else:
                cur.execute("INSERT INTO used_promos VALUES (?, ?)", (uid, txt))
                cur.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (codes[txt], uid))
                con.commit()
                await update.message.reply_text(f"✅ +{codes[txt]} руб!")

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex(f"^{BTN_SUPPORT}$"), lambda u,c: u.message.reply_text(f"🆘 Админ: {ADMIN_USERNAME}")))
    app.add_handler(MessageHandler(filters.Regex(f"^{BTN_WITHDRAW}$"), lambda u,c: u.message.reply_text("Вывод доступен внутри игры.")))
    app.add_handler(MessageHandler(filters.Regex(f"^{BTN_GET_PROMO}$"), lambda u,c: u.message.reply_text("Код: OpenFride")))
    
    # Слушаем данные из WebApp
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, data_handler))
    
    # Слушаем текст (промокоды)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, promo))
    
    print("Бот работает.")
    app.run_polling()

if __name__ == '__main__':
    main()

