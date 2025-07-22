from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import sqlite3
import json
import logging
import requests
import asyncio
from datetime import datetime

# Конфигурация
TOKEN = "8001659110:AAE4JyLTuX5s6zyj5F_CQoW5e-J-FGhosg4"
WEBAPP_URL = "https://star-ruddy-three.vercel.app/"
CRYPTO_PAY_TOKEN = "421215:AAjdPiEHPnyscrlkUMEICJzkonZIZJDkXo9"
CRYPTO_PAY_API = "https://pay.crypt.bot/api"
STARS_RATE = 1.4
MIN_PAYMENT = 10

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
                    CREATE TABLE IF NOT EXISTS inventory (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        item_name TEXT NOT NULL,
                        item_image TEXT,
                        sell_price INTEGER,
                        obtained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                invoice_id TEXT PRIMARY KEY,
                user_id INTEGER,
                stars INTEGER,
                amount_usd REAL,
                status TEXT CHECK(status IN ('pending', 'paid', 'expired')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        ''')

        conn.commit()

async def get_user_data(user_id):
    with sqlite3.connect('users.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT stars FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()

        cursor.execute('''
            SELECT item_name as name, item_image as image, sell_price
            FROM inventory WHERE user_id = ?
        ''', (user_id,))
        inventory = cursor.fetchall()

        return {
            'balance': user['stars'] if user else 0,
            'inventory': [dict(item) for item in inventory]
        }

async def create_crypto_invoice(user_id, stars, amount_usd):
    try:
        headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}
        payload = {
            "asset": "USDT",
            "amount": str(amount_usd),
            "description": f"Пополнение {stars} звезд",
            "paid_btn_url": f"{WEBAPP_URL}?payment_success={user_id}_{stars}",
            "payload": json.dumps({"user_id": user_id, "stars": stars})
        }

        response = requests.post(
            f"{CRYPTO_PAY_API}/createInvoice",
            headers=headers,
            json=payload
        )

        if response.status_code == 200:
            result = response.json().get('result')

            with sqlite3.connect('users.db') as conn:
                conn.execute('''
                    INSERT INTO payments (invoice_id, user_id, stars, amount_usd, status)
                    VALUES (?, ?, ?, ?, ?)
                ''', (result['invoice_id'], user_id, stars, amount_usd, 'pending'))
                conn.commit()

            return result
        else:
            logging.error(f"Crypto Pay error: {response.text}")
            return None

    except Exception as e:
        logging.error(f"Payment error: {e}")
        return None

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    with sqlite3.connect('users.db') as conn:
        # 1. Создаем/обновляем пользователя
        conn.execute('''
            INSERT OR REPLACE INTO users
            (user_id, username, first_name, last_active, stars)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, COALESCE((SELECT stars FROM users WHERE user_id = ?), 0))
        ''', (user_id, username, message.from_user.first_name, user_id))

        # 2. Создаем стартовый инвентарь (если не существует)
        cursor = conn.execute('SELECT 1 FROM inventory WHERE user_id = ? LIMIT 1', (user_id,))
        if not cursor.fetchone():
            conn.execute('''
                INSERT INTO inventory
                (user_id, item_name, item_image, sell_price)
                VALUES (?, 'Стартовый набор', 'starter.png', 10)
            ''', (user_id,))

        # 3. Получаем данные для веб-приложения
        cursor = conn.execute('SELECT stars FROM users WHERE user_id = ?', (user_id,))
        stars = cursor.fetchone()[0]

        cursor = conn.execute('''
            SELECT item_name as name, item_image as image, sell_price
            FROM inventory WHERE user_id = ?
        ''', (user_id,))
        inventory = cursor.fetchall()

        conn.commit()

    # 4. Формируем URL с ВСЕМИ параметрами
    webapp_url = (
        f"https://star-ruddy-three.vercel.app/"
        f"?user_id={user_id}"
        f"&stars={stars}"
        f"&inventory={json.dumps([dict(item) for item in inventory])}"
        f"&username={username}"
    )

    # 5. Отправляем сообщение с кнопкой
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton(
        "🎰 Открыть мини-приложение",
        web_app=types.WebAppInfo(url=webapp_url)
    ))

    await message.answer(
        "🌟 Добро пожаловать в Star Azart!",
        reply_markup=keyboard
    )

@dp.message_handler(commands=['pay'])
async def handle_payment(message: types.Message):
    try:
        user_id = message.from_user.id
        args = message.get_args().split('_')

        if len(args) >= 3 and args[0] == 'pay':
            stars = int(args[2])
            amount_usd = stars * STARS_RATE

            invoice = await create_crypto_invoice(user_id, stars, amount_usd)

            if invoice:
                kb = types.InlineKeyboardMarkup()
                kb.add(types.InlineKeyboardButton(
                    text="💳 Оплатить сейчас",
                    url=invoice['pay_url']
                ))

                await message.answer(
                    f"💎 Счет на {stars} ⭐ ({amount_usd:.2f} USDT)\n\n"
                    f"Ссылка для оплаты действительна 15 минут",
                    reply_markup=kb
                )
            else:
                await message.answer("❌ Не удалось создать счет, попробуйте позже")
        else:
            await message.answer("Используйте команду в формате: /pay_100 (где 100 - количество звезд)")

    except Exception as e:
        logging.error(f"Payment command error: {e}")
        await message.answer("❌ Произошла ошибка, попробуйте позже")

@dp.message_handler(content_types=['web_app_data'])
async def handle_web_app_data(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        user_id = message.from_user.id

        if data['action'] == 'open_case':
            case_price = 10

            with sqlite3.connect('users.db') as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT stars FROM users WHERE user_id = ?', (user_id,))
                user = cursor.fetchone()

                if not user or user['stars'] < case_price:
                    await message.answer("❌ Недостаточно звезд для открытия кейса!")
                    return

                conn.execute('UPDATE users SET stars = stars - ? WHERE user_id = ?',
                            (case_price, user_id))

                conn.execute('''
                    INSERT INTO inventory (user_id, item_name, item_image, sell_price)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, "Предмет", "item.png", 5))

                conn.commit()

            user_data = await get_user_data(user_id)
            webapp_url = f"{WEBAPP_URL}?user_id={user_id}&stars={user_data['balance']}&inventory={json.dumps(user_data['inventory'])}"

            await message.answer(
                "🎉 Кейс успешно открыт!",
                reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(
                    types.KeyboardButton(
                        "🔄 Обновить приложение",
                        web_app=types.WebAppInfo(url=webapp_url)
                    )
                )
            )

    except Exception as e:
        logging.error(f"WebApp error: {e}")
        await message.answer("❌ Произошла ошибка, попробуйте позже")

async def check_payments():
    while True:
        try:
            with sqlite3.connect('users.db') as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM payments WHERE status = "pending"')
                pending_payments = cursor.fetchall()

                headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}

                for payment in pending_payments:
                    invoice_id = payment['invoice_id']
                    response = requests.get(
                        f"{CRYPTO_PAY_API}/getInvoices?invoice_ids={invoice_id}",
                        headers=headers
                    )

                    if response.status_code == 200:
                        invoice = response.json().get('result', {}).get('items', [{}])[0]

                        if invoice.get('status') == 'paid':
                            conn.execute('''
                                UPDATE users
                                SET stars = stars + ?
                                WHERE user_id = ?
                            ''', (payment['stars'], payment['user_id']))

                            conn.execute('''
                                UPDATE payments
                                SET status = 'paid'
                                WHERE invoice_id = ?
                            ''', (invoice_id,))

                            conn.commit()

                            await bot.send_message(
                                payment['user_id'],
                                f"✅ Ваш баланс пополнен на {payment['stars']} ⭐"
                            )

        except Exception as e:
            logging.error(f"Payment check error: {e}")

        await asyncio.sleep(60)

if __name__ == '__main__':
    init_db()
    loop = asyncio.get_event_loop()
    loop.create_task(check_payments())
    executor.start_polling(dp, skip_updates=True)