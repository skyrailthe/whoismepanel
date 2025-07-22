import json
import os
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app)

# Загрузка пользователей из файла
def load_users():
    try:
        with open('users.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}

# Сохранение пользователей в файл
def save_users():
    with open('users.json', 'w') as f:
        json.dump(users, f)

@socketio.on('clear_users')
def handle_clear_users():
    global users
    users = {}  # Очищаем пользователей в памяти

    # Сохраняем пустой объект в файл
    save_users()

    emit('update_user_list', users, broadcast=True)  # Обновляем всех клиентов


# Загрузка пользователей при старте
users = load_users()

@app.route('/')
def index():
    return render_template('index.html')
  
@socketio.on('check_user')
def handle_check_user(data):
    user_id = data['userId']
    
    # Проверка наличия пользователя на сервере
    if user_id in users:
        # Если пользователь существует, отправляем обратно никнейм
        emit('user_exists', users[user_id])
    else:
        # Если пользователь не найден
        emit('user_not_found')


@socketio.on('join')
def handle_join(data):
    user_id = data['userId']
    nickname = data['nickname']
    
    if user_id not in users:
      users[user_id] = {
          'nickname': nickname,
          'text': '',
          'queue_position': len(users) + 1,  # Указание позиции в очереди
          'show_next_button': False  # Добавляем это поле
      }
    else:
      users[user_id]['nickname'] = nickname
      users[user_id]['queue_position'] = len(users) + 1  # Переписываем позицию
      users[user_id]['show_next_button'] = False  # Обновляем состояние кнопки

    save_users()
    emit('update_user_list', users, broadcast=True)
    emit_next_user()  # Обновляем следующий пользователь в очереди


def emit_next_user():
    # Сортируем пользователей по их позиции в очереди
    sorted_users = sorted(users.items(), key=lambda x: x[1]['queue_position'])
    if sorted_users:
        next_user_id = sorted_users[0][0]  # Берем первого в очереди
        # Сбрасываем кнопку "End Turn" у всех пользователей
        for uid in users.keys():
            users[uid]['show_next_button'] = False  # Скрываем кнопку для всех
        # Показываем кнопку "End Turn" только у следующего пользователя
        users[next_user_id]['show_next_button'] = True

    emit('update_user_list', users, broadcast=True)  # Отправляем обновленный список пользователям


@socketio.on('update_text')
def handle_update_text(data):
    user_id = data['userId']
    text = data['text']
    if user_id in users:
        users[user_id]['text'] = text
    emit('update_user_list', users, broadcast=True)

@socketio.on('remove_user')
def handle_remove_user(user_id):
    if user_id in users:
        del users[user_id]
        # Пересчитываем позиции в очереди
        for index, (uid, user_data) in enumerate(sorted(users.items(), key=lambda x: x[1]['queue_position'])):
            user_data['queue_position'] = index + 1  # Обновляем позицию (начиная с 1)

        save_users()  # Сохраняем изменения после обновления
        emit_next_user()  # Обновляем следующий пользователь в очереди

    # После удаления пользователя, отправляем обновленный список пользователям
    emit('update_user_list', users, broadcast=True)

    
@socketio.on('end_turn')
def handle_end_turn(user_id):
    if user_id in users:
        # Определяем текущую позицию пользователя в очереди
        current_position = users[user_id]['queue_position']
        
        # Получаем отсортированный список пользователей
        sorted_users = sorted(users.items(), key=lambda x: x[1]['queue_position'])
        
        # Проверяем, есть ли пользователи в очереди
        if len(sorted_users) > 1:  # Если больше одного пользователя
            # Находим следующего пользователя в очереди
            next_position = (current_position) % len(sorted_users)  # Переход к следующему пользователю
            next_user_id = sorted_users[next_position][0]  # Берем ID следующего пользователя
            
            # Сбрасываем отображение кнопки для всех пользователей
            for uid in users.keys():
                users[uid]['show_next_button'] = False  # Скрываем кнопку для всех
            
            # Отображаем кнопку "Next" для следующего пользователя
            users[next_user_id]['show_next_button'] = True  # Устанавливаем для следующего
            
            # Выделяем карточку текущего пользователя
            users[user_id]['highlight'] = True  # Выделяем текущего пользователя
            users[next_user_id]['highlight'] = False  # Сбрасываем выделение для следующего

        # Сохраняем изменения в JSON
        save_users()  # Сохраняем изменения в JSON
        
        # Уведомляем всех пользователей об обновлении очереди
        emit('update_user_list', users, broadcast=True)




@socketio.on('disconnect')
def handle_disconnect():
    emit('update_user_list', users, broadcast=True)

@socketio.on('check_user_exists')
def handle_check_user_exists(data):
    user_id = data['userId']
    exists = user_id in users
    emit('user_exists', exists)

@socketio.on('request_user_list')
def handle_request_user_list():
    emit('update_user_list', users)

if __name__ == '__main__':
    socketio.run(app, debug=True)
