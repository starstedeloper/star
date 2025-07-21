from flask import Flask, jsonify, request
import sqlite3
import json
import random

app = Flask(__name__)

# 1. Загружаем ваш конфиг кейсов
with open('config.json') as f:
    CASES = json.load(f)['cases']  # Ваш файл config.json

# 2. Эндпоинт для открытия кейса
@app.route('/open-case', methods=['POST'])
def open_case():
    user_id = request.json.get('user_id')
    case_type = request.json.get('case_type')

    # 3. Находим нужный кейс
    case = next((c for c in CASES if c['type'] == case_type), None)
    if not case:
        return jsonify({'error': 'Кейс не найден'}), 404

    # 4. Выбираем случайный предмет (ваша логика из caseOpening.js)
    won_item = random.choices(
        case['items'],
        weights=[i['chance'] for i in case['items']]
    )[0]

    # 5. Возвращаем результат
    return jsonify({
        'item': won_item,
        'message': 'Кейс успешно открыт!'
    })

if __name__ == '__main__':
    app.run(port=5000)  # Запуск сервера