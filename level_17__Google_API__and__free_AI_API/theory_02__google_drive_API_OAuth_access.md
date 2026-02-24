### Шаг 1. Создать OAuth Client ID

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/apis/credentials).
2. Выберите проект или создайте новый проект.
3. В меню слева: **APIs & Services → Credentials**.
4. Нажмите **Create Credentials → OAuth Client ID**.
5. Если появится сообщение “Configure consent screen”, нажмите **Configure** и заполните:

   * User Type: **External** (для личного Gmail)
   * App name: любое (например, `My Backup Script`)
   * Email: ваш Gmail
   * Остальные поля можно оставить по умолчанию
6. Сохраните Consent Screen.
7. Создайте **OAuth Client ID**:

   * Application type: **Desktop app**
   * Name: например, `Server OAuth`
8. После создания скачайте **JSON файл** (`client_secret.json`) — он нужен для первого шага аутентификации.
 
### Шаг 2. Добавить себя как тестера

1. Перейдите в Google Cloud Console → APIs & Services → OAuth consent screen → Audience
2. Прокрутите до Test users (Тестовые пользователи)
3. Нажмите Add users
4. Введите свой Gmail
5. Сохраните изменения

После этого ваш аккаунт сможет проходить OAuth flow для этого приложения

---

### Шаг 3. Включить Google Drive API

1. В левом меню: APIs & Services → Library 
2. Найдите Google Drive API
3. Нажмите Enable

---

### Шаг 4. Установить зависимости Python

```bash
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

pip freeze > requirements.txt
```

---

### Шаг 5. Первый запуск и получение токена (пропускаем)

Создайте файл `get_token.py`:

```python
from google_auth_oauthlib.flow import InstalledAppFlow
import json

SCOPES = ['https://www.googleapis.com/auth/drive.file']

flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
creds = flow.run_local_server(port=0)  # откроет браузер и попросит авторизацию

# Сохраняем токены для будущего использования
with open('token.json', 'w') as token_file:
    token_file.write(creds.to_json())

print("Токен сохранён в token.json")
```

* При запуске скрипта откроется браузер
* Вы должны разрешить доступ к вашему Google Drive
* После этого в папке появится `token.json` с **access + refresh token**

---

### Шаг 6. Использовать токен на сервере (пропускаем)

Теперь серверный скрипт может работать без браузера:

```python
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Загружаем сохранённый токен
creds = Credentials.from_authorized_user_file('token.json', SCOPES)
service = build('drive', 'v3', credentials=creds, cache_discovery=False)

# Загрузка файла
file_metadata = {'name': 'example.txt'}
media = MediaFileUpload('example.txt', resumable=True)
file = service.files().create(
    body=file_metadata,
    media_body=media,
    fields='id'
).execute()

print("Файл загружен. ID:", file.get('id'))
```

Скрипт будет использовать **refresh token**, чтобы обновлять access token автоматически.
⚠️ Больше не нужен браузер для последующих запусков.

---

### Шаг 7. Универсальный скрипт

1. Если токена нет, то придётся 1 раз пройти через браузерное подтверждение токена
2. После этого подтверждение через браузер уже не нужно.

```python
import logging
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os

logging.basicConfig(level=logging.INFO)

SCOPES = ['https://www.googleapis.com/auth/drive.file']

TOKEN_FILE = 'token.json'                       # Файл для сохранения токена
CLIENT_SECRET_FILE = 'client_secret.json'       # Ваш OAuth client secret
FILE_TO_UPLOAD = 'example.txt'                  # файл, который хотите загрузить
FOLDER_ID = '1fQl9NMvUBfnQA8pa0DRoxvSqPEDhUo93' # ID папки на Google Drive


# --- Шаг 1: Получаем credentials ---
def get_credentials():
    if os.path.exists(TOKEN_FILE):
        logging.info("Загружаем токен из файла...")
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    else:
        logging.info("Токен не найден, запускаем OAuth flow...")
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token_file:
            token_file.write(creds.to_json())
        logging.info(f"Токен сохранён в {TOKEN_FILE}")
    return creds

# --- Шаг 2: Инициализация сервиса ---
creds = get_credentials()
service = build('drive', 'v3', credentials=creds, cache_discovery=False)

# --- Шаг 3: Загрузка файла ---
def upload_file(file_path, folder_id=None):
    file_name = os.path.basename(file_path)
    file_metadata = {'name': file_name}
    if folder_id:
        file_metadata['parents'] = [folder_id]

    media = MediaFileUpload(file_path, resumable=True)
    request = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    )

    response = None
    last_percent = 0
    while response is None:
        status, response = request.next_chunk()
        if status:
            current_percent = int(status.progress() * 100)
            if current_percent - last_percent >= 10:
                logging.info(f"Загружено: {current_percent}%")
                last_percent = current_percent

    logging.info(f"Файл загружен. ID: {response.get('id')}")
    return response.get('id')

if __name__ == "__main__":
    upload_file(FILE_TO_UPLOAD, FOLDER_ID)
```


