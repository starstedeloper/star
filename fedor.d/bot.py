from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import sqlite3
import requests
import logging
from datetime import datetime

# Конфигурация
TOKEN = "8001659110:AAE4JyLTuX5s6zyj5F_CQoW5e-J-FGhosg4"
CRYPTO_PAY_API = "https://pay.crypt.bot/api"
CRYPTO_PAY_TOKEN = "421215:AAjdPiEHPnyscrlkUMEICJzkonZIZJDkXo9"
STARS_RATE = 1.4
MIN_PAYMENT = 10
WEBAPP_URL = "https://your-webapp-url.vercel.app/"

# Инициализация
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)

def init_db():
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                stars INTEGER DEFAULT 0,
                last_active TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                invoice_id TEXT PRIMARY KEY,
                user_id INTEGER,
                stars INTEGER,
                amount_rub REAL,
                status TEXT CHECK(status IN ('pending', 'paid', 'expired')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_name TEXT,
                item_image TEXT,
                sell_price INTEGER,
                withdraw_price INTEGER,
                obtained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        ''')

        conn.commit()

# Команда /start
@dp.message_handler(commands=['start', 'menu'])
async def start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    with sqlite3.connect('users.db') as conn:
        conn.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, last_active)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, username, message.from_user.first_name))
        conn.commit()

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton(
        "🎰 Открыть мини-приложение",
        web_app=types.WebAppInfo(url=WEBAPP_URL)
    ))

    await message.answer(
        "🌟 Добро пожаловать в Star Azart!\n\n"
        "Испытайте удачу в наших эксклюзивных кейсах!",
        reply_markup=keyboard
    )

# Обработка платежей
@dp.message_handler(commands=['pay'])
async def handle_payment(message: types.Message):
    user_id = message.from_user.id
    amount = int(message.get_args()) if message.get_args() else 100

    amount_rub = amount * STARS_RATE
    invoice = await create_crypto_invoice(user_id, amount, amount_rub)

    if invoice:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(
            text="💳 Оплатить сейчас",
            url=invoice['pay_url']
        ))

        await message.answer(
            f"💎 Счет на {amount} ⭐ ({amount_rub}₽)\n\n"
            f"Ссылка для оплаты действительна 15 минут",
            reply_markup=kb
        )

async def create_crypto_invoice(user_id, stars, amount_rub):
    try:
        headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}
        payload = {
            "asset": "USDT",
            "amount": str(amount_rub),
            "description": f"Пополнение {stars} звезд",
            "paid_btn_url": f"{WEBAPP_URL}?payment_success={user_id}_{stars}"
        }

        response = requests.post(
            f"{CRYPTO_PAY_API}/createInvoice",
            headers=headers,
            json=payload
        )
        return response.json().get('result')
    except Exception as e:
        logging.error(f"Payment error: {e}")
        return None

if __name__ == '__main__':
    init_db()
    executor.start_polling(dp, skip_updates=True)