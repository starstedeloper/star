from flask import Flask, jsonify, request
import sqlite3
import json
import random

app = Flask(__name__)

# Загрузка конфига кейсов
with open('config.json') as f:
    CASES = json.load(f)['cases']

# Подключение к БД
def get_db():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

# Эндпоинт для получения данных пользователя
@app.route('/api/user')
def get_user():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400

    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()

    if user:
        return jsonify({
            'balance': user['stars'],
            'inventory': get_user_inventory(user_id)
        })
    return jsonify({'error': 'User not found'}), 404

# Эндпоинт для открытия кейса
@app.route('/api/open-case', methods=['POST'])
def open_case():
    data = request.json
    user_id = data.get('user_id')
    case_type = data.get('case_type')

    case = next((c for c in CASES if c['type'] == case_type), None)
    if not case:
        return jsonify({'error': 'Case not found'}), 404

    # Проверка баланса
    conn = get_db()
    user = conn.execute('SELECT stars FROM users WHERE user_id = ?', (user_id,)).fetchone()
    if not user or user['stars'] < case['price']:
        conn.close()
        return jsonify({'error': 'Not enough stars'}), 400

    # Выбор предмета
    won_item = random.choices(
        case['items'],
        weights=[i['chance'] for i in case['items']]
    )[0]

    # Обновление баланса
    conn.execute('UPDATE users SET stars = stars - ? WHERE user_id = ?',
                (case['price'], user_id))
    conn.commit()
    conn.close()

    return jsonify({
        'item': won_item,
        'new_balance': user['stars'] - case['price']
    })

    conn.execute('''
        INSERT INTO inventory
        (user_id, item_name, item_image, sell_price, withdraw_price)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        user_id,
        won_item['name'],
        won_item['image'],
        won_item['sell_price'],
        won_item['withdraw_price']
    ))
    conn.commit()

def get_user_inventory(user_id):
    conn = get_db()
    items = conn.execute('''
        SELECT
            id,
            item_name as name,
            item_image as image,
            sell_price,
            withdraw_price
        FROM inventory
        WHERE user_id = ?
    ''', (user_id,)).fetchall()
    conn.close()
    return [dict(item) for item in items]

if __name__ == '__main__':
    app.run(port=5000)