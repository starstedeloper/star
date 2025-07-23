# ==============================================================================
# ПОЛНЫЙ И ИСПРАВЛЕННЫЙ ФАЙЛ BOT.PY
# ==============================================================================

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import sqlite3
import json
import logging
import requests
import asyncio
from datetime import datetime, timedelta
import random
import urllib.parse

# Конфигурация
TOKEN = "8001659110:AAE4JyLTuX5s6zyj5F_CQoW5e-J-FGhosg4"
WEBAPP_URL = "https://star-ruddy-three.vercel.app/"
ADMIN_IDS = [8132062572]  # ID администратора
CRYPTO_PAY_TOKEN = "421215:AAjdPiEHPnyscrlkUMEICJzkonZIZJDkXo9"
CRYPTO_PAY_API = "https://pay.crypt.bot/api"
STARS_RATE = 1.4  # 1 звезда = 1.4 рубля
MIN_PAYMENT = 10  # Минимальное количество звезд для пополнения

# Инициализация
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)

# Инициализация базы данных
def init_db():
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()

        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                stars INTEGER DEFAULT 0,
                last_active TIMESTAMP,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_admin BOOLEAN DEFAULT FALSE
            )
        ''')

        # Таблица инвентаря
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_id INTEGER,
                item_name TEXT NOT NULL,
                item_image TEXT,
                emoji TEXT,
                sell_price INTEGER,
                withdraw_price INTEGER,
                obtained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_withdrawn BOOLEAN DEFAULT FALSE,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')

        # Таблица платежей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                invoice_id TEXT PRIMARY KEY,
                user_id INTEGER,
                stars INTEGER,
                amount_usd REAL,
                status TEXT CHECK(status IN ('pending', 'paid', 'expired')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                paid_at TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        ''')

        # Таблица кейсов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price INTEGER NOT NULL,
                image TEXT,
                emoji TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица предметов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                image TEXT,
                emoji TEXT,
                sell_price INTEGER NOT NULL,
                withdraw_price INTEGER NOT NULL,
                rarity TEXT CHECK(rarity IN ('common', 'rare', 'epic', 'legendary')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица предметов в кейсах
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS case_items (
                case_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                chance REAL NOT NULL,
                PRIMARY KEY (case_id, item_id),
                FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE,
                FOREIGN KEY(item_id) REFERENCES items(id) ON DELETE CASCADE
            )
        ''')

        # Таблица выводов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                status TEXT CHECK(status IN ('pending', 'completed', 'rejected')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                admin_id INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(item_id) REFERENCES inventory(id)
            )
        ''')

        # Создаем администратора если его нет
        for admin_id in ADMIN_IDS:
            cursor.execute('''
                INSERT OR IGNORE INTO users (user_id, is_admin)
                VALUES (?, TRUE)
            ''', (admin_id,))

        conn.commit()

# Загрузка начальных данных (кейсы и предметы)
async def load_initial_data():
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT 1 FROM cases LIMIT 1')
        if not cursor.fetchone():
            cases = [
                ('Обычный кейс', 10, 'common_case.png', '📦'),
                ('Редкий кейс', 25, 'rare_case.png', '🎁'),
                ('Эпический кейс', 50, 'epic_case.png', '💎'),
                ('Легендарный кейс', 100, 'legendary_case.png', '🏆')
            ]
            cursor.executemany('INSERT INTO cases (name, price, image, emoji) VALUES (?, ?, ?, ?)', cases)
            
            items = [
                ('Сердце', 'heart.png', '❤️', 15, 15, 'common'),
                ('Плюшевый мишка', 'teddy_bear.png', '🧸', 15, 15, 'common'),
                ('Подарок', 'gift.png', '🎁', 25, 25, 'rare'),
                ('Роза', 'rose.png', '🌹', 25, 25, 'rare'),
                ('Торт', 'cake.png', '🎂', 50, 50, 'epic'),
                ('Букет', 'bouquet.png', '💐', 50, 50, 'epic'),
                ('Ракета', 'rocket.png', '🚀', 50, 50, 'epic'),
                ('Кубок', 'trophy.png', '🏆', 100, 100, 'legendary'),
                ('Кольцо', 'ring.png', '💍', 100, 100, 'legendary'),
                ('Алмаз', 'diamond.png', '💎', 100, 100, 'legendary')
            ]
            cursor.executemany('INSERT INTO items (name, image, emoji, sell_price, withdraw_price, rarity) VALUES (?, ?, ?, ?, ?, ?)', items)
            conn.commit()


# Получение данных пользователя
async def get_user_data(user_id):
    with sqlite3.connect('users.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT stars FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()

        cursor.execute('''
            SELECT 
                i.id, i.item_name as name, i.item_image as image, i.emoji, 
                i.sell_price, i.withdraw_price
            FROM inventory i
            WHERE i.user_id = ? AND i.is_withdrawn = FALSE
        ''', (user_id,))
        inventory = cursor.fetchall()

        return {
            'balance': user['stars'] if user else 0,
            'inventory': [dict(item) for item in inventory]
        }

# Создание крипто-инвойса
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

        response = requests.post(f"{CRYPTO_PAY_API}/createInvoice", headers=headers, json=payload)

        if response.status_code == 201 or response.status_code == 200:
            result = response.json().get('result')
            with sqlite3.connect('users.db') as conn:
                conn.execute('''
                    INSERT INTO payments (invoice_id, user_id, stars, amount_usd, status)
                    VALUES (?, ?, ?, ?, 'pending')
                ''', (result['invoice_id'], user_id, stars, amount_usd))
                conn.commit()
            return result
        else:
            logging.error(f"Crypto Pay error: {response.text}")
            return None
    except Exception as e:
        logging.error(f"Payment error: {e}")
        return None

# Продажа предмета
async def sell_item(user_id, item_id):
    with sqlite3.connect('users.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT id, sell_price FROM inventory WHERE id = ? AND user_id = ? AND is_withdrawn = FALSE', (item_id, user_id))
            item = cursor.fetchone()
            if not item: return False, "Предмет не найден"

            cursor.execute('UPDATE users SET stars = stars + ? WHERE user_id = ?', (item['sell_price'], user_id))
            cursor.execute('DELETE FROM inventory WHERE id = ?', (item_id,))
            conn.commit()
            return True, None
        except Exception as e:
            conn.rollback(); logging.error(f"Error selling item: {e}"); return False, "Ошибка при продаже предмета"

# Запрос на вывод предмета
async def request_withdrawal(user_id, item_id):
    with sqlite3.connect('users.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT id FROM inventory WHERE id = ? AND user_id = ? AND is_withdrawn = FALSE', (item_id, user_id))
            item = cursor.fetchone()
            if not item: return False, "Предмет не найден"
            
            cursor.execute('INSERT INTO withdrawals (user_id, item_id, status) VALUES (?, ?, \'pending\')', (user_id, item_id))
            cursor.execute('UPDATE inventory SET is_withdrawn = TRUE WHERE id = ?', (item_id,))
            conn.commit()
            return True, None
        except Exception as e:
            conn.rollback(); logging.error(f"Error requesting withdrawal: {e}"); return False, "Ошибка при запросе вывода"

# Проверка платежей
async def check_payments():
    while True:
        await asyncio.sleep(60)
        try:
            with sqlite3.connect('users.db') as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM payments WHERE status = 'pending' AND created_at > datetime('now', '-1 hour')")
                pending_payments = cursor.fetchall()
                if not pending_payments: continue

                headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}
                for payment in pending_payments:
                    response = requests.get(f"{CRYPTO_PAY_API}/getInvoices?invoice_ids={payment['invoice_id']}", headers=headers)
                    if response.status_code != 200: continue
                    
                    invoice = response.json().get('result', {}).get('items', [{}])[0]
                    if invoice.get('status') == 'paid':
                        cursor.execute('UPDATE users SET stars = stars + ? WHERE user_id = ?', (payment['stars'], payment['user_id']))
                        cursor.execute("UPDATE payments SET status = 'paid', paid_at = CURRENT_TIMESTAMP WHERE invoice_id = ?", (payment['invoice_id'],))
                        conn.commit()
                        await bot.send_message(payment['user_id'], f"✅ Ваш баланс пополнен на {payment['stars']} ⭐")
                    elif invoice.get('status') == 'expired':
                        cursor.execute("UPDATE payments SET status = 'expired' WHERE invoice_id = ?", (payment['invoice_id'],))
                        conn.commit()
        except Exception as e:
            logging.error(f"Payment check error: {e}")

# Общая функция для вызова при запросе оплаты
async def process_payment_request(user_id, stars_to_pay):
    if stars_to_pay < MIN_PAYMENT:
        await bot.send_message(user_id, f"Минимальная сумма пополнения: {MIN_PAYMENT} ⭐")
        return

    amount_usd = round(stars_to_pay * STARS_RATE, 2)
    invoice = await create_crypto_invoice(user_id, stars_to_pay, amount_usd)

    if invoice:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(text="💳 Оплатить сейчас", url=invoice['pay_url']))
        await bot.send_message(user_id, f"💎 Счет на {stars_to_pay} ⭐ ({amount_usd:.2f} USDT)\n\nСсылка для оплаты действительна 1 час.", reply_markup=kb)
    else:
        await bot.send_message(user_id, "❌ Не удалось создать счет, попробуйте позже")

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        
        # ИСПРАВЛЕНИЕ №1: Проверяем, существует ли пользователь, чтобы не давать бонус повторно
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        user_exists = cursor.fetchone()

        if not user_exists:
            # Новый пользователь: добавляем в базу и даем бонус
            cursor.execute('''
                INSERT INTO users (user_id, username, first_name, last_name, last_active, stars)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, 10)
            ''', (user_id, username, message.from_user.first_name, message.from_user.last_name))
            
            cursor.execute('''
                INSERT INTO inventory (user_id, item_id, item_name, item_image, emoji, sell_price, withdraw_price)
                SELECT ?, id, name, image, emoji, sell_price, withdraw_price
                FROM items WHERE rarity = 'common' ORDER BY RANDOM() LIMIT 1
            ''', (user_id,))
            
            await message.answer("🎉 Вы получили стартовый бонус: 10 ⭐ и случайный предмет!")
        else:
            # Существующий пользователь: просто обновляем данные
            cursor.execute('''
                UPDATE users SET
                username = ?,
                first_name = ?,
                last_name = ?,
                last_active = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (username, message.from_user.first_name, message.from_user.last_name, user_id))
        
        conn.commit()

    # Проверяем аргументы (deep link) для оплаты
    args = message.get_args()
    if args and args.startswith('pay_'):
        try:
            parts = args.split('_')
            if len(parts) == 3:
                await process_payment_request(user_id, int(parts[2]))
            else:
                await message.answer("Ошибка в ссылке для оплаты.")
        except (ValueError, IndexError):
            await message.answer("Некорректная ссылка для оплаты.")
        return

    # Передаем ВСЕ данные в URL для инициализации приложения
    user_data = await get_user_data(user_id)
    inventory_json_str = json.dumps(user_data['inventory'])
    inventory_encoded = urllib.parse.quote(inventory_json_str)
    
    webapp_url = (
        f"{WEBAPP_URL}?"
        f"user_id={user_id}&"
        f"stars={user_data['balance']}&"
        f"inventory={inventory_encoded}"
    )

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton(
        "🎰 Открыть мини-приложение",
        web_app=types.WebAppInfo(url=webapp_url)
    ))

    await message.answer(
        f"🌟 Добро пожаловать в Star Azart, {message.from_user.first_name}!\n\n"
        "Нажмите кнопку ниже, чтобы открыть игровое приложение:",
        reply_markup=keyboard
    )

@dp.message_handler(content_types=['web_app_data'])
async def handle_web_app_data(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        user_id = message.from_user.id
        action = data.get('action')

        if action == 'open_case':
            # ИСПРАВЛЕНИЕ №3: Принимаем результат открытия кейса от клиента
            case_type = data.get('caseType')
            won_item = data.get('wonItem')

            if not case_type or not won_item:
                logging.warning(f"Invalid open_case data from {user_id}")
                return

            case_prices = {'common': 10, 'rare': 25, 'epic': 50, 'legendary': 100}
            case_price = case_prices.get(case_type)
            
            if not case_price:
                logging.warning(f"Invalid case_type '{case_type}' from {user_id}")
                return
                
            with sqlite3.connect('users.db') as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute('SELECT stars FROM users WHERE user_id = ?', (user_id,))
                    user_stars = cursor.fetchone()
                    if not user_stars or user_stars[0] < case_price:
                        logging.warning(f"Insufficient funds for {user_id} to open {case_type} case.")
                        return

                    cursor.execute('UPDATE users SET stars = stars - ? WHERE user_id = ?', (case_price, user_id))
                    
                    cursor.execute('SELECT id, image, withdraw_price FROM items WHERE name = ?', (won_item['name'],))
                    item_details = cursor.fetchone()
                    item_db_id = item_details[0] if item_details else None
                    item_image = item_details[1] if item_details else ''
                    item_withdraw_price = item_details[2] if item_details else won_item['sell_price']

                    cursor.execute('''
                        INSERT INTO inventory (user_id, item_id, item_name, item_image, emoji, sell_price, withdraw_price)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (user_id, item_db_id, won_item['name'], item_image, won_item.get('emoji', '🎁'), won_item['sell_price'], item_withdraw_price))
                    
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    logging.error(f"Error processing won item for {user_id}: {e}")

        elif action == 'sell_item':
            item_id = data.get('item_id')
            if item_id: await sell_item(user_id, item_id)

        elif action == 'withdraw_item':
            item_id = data.get('item_id')
            if not item_id: return

            success, error = await request_withdrawal(user_id, item_id)
            if success:
                for admin_id in ADMIN_IDS:
                    try:
                        await bot.send_message(
                            admin_id,
                            f"🆕 Новый запрос на вывод предмета от @{message.from_user.username or user_id}\nID предмета: {item_id}"
                        )
                    except Exception as e:
                        logging.error(f"Error notifying admin: {e}")

    except json.JSONDecodeError:
        logging.error("JSONDecodeError in web_app_data")
    except Exception as e:
        logging.error(f"WebApp error: {e}")

@dp.message_handler(commands=['admin'])
async def admin_panel(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("❌ У вас нет прав администратора")

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"))
    keyboard.add(types.InlineKeyboardButton("📝 Запросы на вывод", callback_data="admin_withdrawals"))
    await message.answer("👑 Панель администратора", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data.startswith('admin_'))
async def process_admin_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in ADMIN_IDS:
        return await bot.answer_callback_query(callback_query.id, "У вас нет прав")

    action = callback_query.data
    await bot.answer_callback_query(callback_query.id)

    if action == 'admin_stats':
        with sqlite3.connect('users.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) as users FROM users')
            users = cursor.fetchone()['users']
            cursor.execute('SELECT SUM(stars) as stars FROM users')
            stars = cursor.fetchone()['stars'] or 0
            cursor.execute("SELECT COUNT(*) as payments, SUM(amount_usd) as amount FROM payments WHERE status = 'paid'")
            p = cursor.fetchone()
            await bot.send_message(user_id, f"📊 Статистика:\n\n👥 Пользователей: {users}\n💫 Всего звезд: {stars}\n💰 Платежей: {p['payments'] or 0} на {p['amount'] or 0:.2f} USDT")

    elif action == 'admin_withdrawals':
        with sqlite3.connect('users.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT w.id, u.username, u.first_name, i.item_name, i.emoji, w.created_at
                FROM withdrawals w JOIN users u ON w.user_id = u.user_id JOIN inventory i ON w.item_id = i.id
                WHERE w.status = 'pending' ORDER BY w.created_at
            ''')
            withdrawals = cursor.fetchall()
            if not withdrawals:
                return await bot.send_message(user_id, "Нет активных запросов на вывод")
            for w in withdrawals:
                kb = types.InlineKeyboardMarkup()
                kb.add(types.InlineKeyboardButton("✅", callback_data=f"approve_{w['id']}"), types.InlineKeyboardButton("❌", callback_data=f"reject_{w['id']}"))
                await bot.send_message(user_id, f"🔄 Запрос #{w['id']}\n@{w['username']} ({w['first_name']})\n{w['emoji']} {w['item_name']}", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith(('approve_', 'reject_')))
async def process_withdrawal_action(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in ADMIN_IDS: return

    action, withdrawal_id = callback_query.data.split('_')
    
    with sqlite3.connect('users.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT w.id, w.user_id, i.id as item_inventory_id, i.item_name, i.emoji
            FROM withdrawals w JOIN inventory i ON w.item_id = i.id
            WHERE w.id = ? AND w.status = 'pending'
        ''', (withdrawal_id,))
        info = cursor.fetchone()
        if not info:
            return await bot.answer_callback_query(callback_query.id, "Запрос уже обработан")

        if action == 'approve':
            cursor.execute("UPDATE withdrawals SET status = 'completed', admin_id = ? WHERE id = ?", (user_id, withdrawal_id))
            conn.commit()
            await bot.send_message(info['user_id'], f"✅ Ваш вывод предмета {info['emoji']} {info['item_name']} одобрен!")
            await callback_query.message.edit_text(f"{callback_query.message.text}\n\n✅ ОДОБРЕНО")
        elif action == 'reject':
            cursor.execute("UPDATE withdrawals SET status = 'rejected', admin_id = ? WHERE id = ?", (user_id, withdrawal_id))
            cursor.execute("UPDATE inventory SET is_withdrawn = FALSE WHERE id = ?", (info['item_inventory_id'],))
            conn.commit()
            await bot.send_message(info['user_id'], f"❌ Ваш вывод предмета {info['emoji']} {info['item_name']} отклонен.")
            await callback_query.message.edit_text(f"{callback_query.message.text}\n\n❌ ОТКЛОНЕНО")
    
    await bot.answer_callback_query(callback_query.id, "Выполнено")

if __name__ == '__main__':
    init_db()
    loop = asyncio.get_event_loop()
    loop.create_task(load_initial_data())
    loop.create_task(check_payments())
    executor.start_polling(dp, skip_updates=True)
