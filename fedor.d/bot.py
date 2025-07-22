from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import sqlite3
import json
import logging
from datetime import datetime

# Конфигурация
TOKEN = "8001659110:AAE4JyLTuX5s6zyj5F_CQoW5e-J-FGhosg4"
WEBAPP_URL = "https://your-webapp-url.vercel.app/"
STARS_RATE = 1.4

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
                user_id INTEGER,
                item_name TEXT,
                item_image TEXT,
                sell_price INTEGER,
                withdraw_price INTEGER,
                obtained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
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

    user_data = await get_user_data(user_id)
    webapp_url = f"{WEBAPP_URL}?user_id={user_id}&stars={user_data['balance']}&inventory={json.dumps(user_data['inventory'])}"

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton(
        "🎰 Открыть мини-приложение",
        web_app=types.WebAppInfo(url=webapp_url)
    ))

    await message.answer(
        "🌟 Добро пожаловать в Star Azart!\n\n"
        "Испытайте удачу в наших эксклюзивных кейсах!",
        reply_markup=keyboard
    )

@dp.message_handler(content_types=['web_app_data'])
async def handle_web_app_data(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        user_id = message.from_user.id

        if data['action'] == 'open_case':
            case_price = 10  # Пример цены кейса
            with sqlite3.connect('users.db') as conn:
                conn.execute('UPDATE users SET stars = stars - ? WHERE user_id = ?',
                            (case_price, user_id))

                # Добавляем случайный предмет в инвентарь
                conn.execute('''
                    INSERT INTO inventory (user_id, item_name, item_image, sell_price)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, "Предмет", "item.png", 5))

                conn.commit()

            # Отправляем обновленные данные
            user_data = await get_user_data(user_id)
            webapp_url = f"{WEBAPP_URL}?user_id={user_id}&stars={user_data['balance']}&inventory={json.dumps(user_data['inventory'])}"

            await message.answer(
                "Кейс успешно открыт!",
                reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(
                    types.KeyboardButton(
                        "🔄 Обновить приложение",
                        web_app=types.WebAppInfo(url=webapp_url)
                    )
                )
            )

    except Exception as e:
        logging.error(f"WebApp error: {e}")
        await message.answer("Произошла ошибка, попробуйте позже")

if __name__ == '__main__':
    init_db()
    executor.start_polling(dp, skip_updates=True)