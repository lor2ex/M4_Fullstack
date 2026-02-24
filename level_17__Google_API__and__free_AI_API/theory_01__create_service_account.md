### Что такое сервисный аккаунт Google?

Service Account — это **отдельный “технический” пользователь Google**.

Он:

* ❌ НЕ имеет доступа к вашим ресурсам Google автоматически
* ✅ Имеет свой собственный Drive, Gmail и т.д.
* ✅ Может получить доступ к вашим Google-ресурсам, если вы их "расшарите" на его email

---

### Шаг 1. Создать Service Account

1. Откройте Google Cloud Console: https://console.cloud.google.com
2. Выберите (создайте) проект: 
   * "Select project" → "New Project"
   * Введите название проекта → Create
3. Перейдите:
   * **IAM & Admin → Service Accounts**
4. Нажмите **Create Service Account**
5. Введите имя → Create
6. Роль можно не назначать (для Drive API не требуется)
7. Сохраните имя `service-account-name`
   (он выглядит примерно так:
   `java-rush@javarush-487913.iam.gserviceaccount.com`)
8. Нажмите **Done**

---

### Шаг 2. Создать JSON-ключ

1. В списке Service Accounts нажмите на созданный аккаунт
2. Перейдите во вкладку **Keys**
3. Нажмите **Add Key → Create new key**
4. Выберите **JSON**
5. Скачайте файл — например:

```
service_account.json
```

---

### Шаг 3. Включить Google Drive API

1. В левом меню: APIs & Services → Library 
2. Найдите Google Drive API
3. Нажмите Enable

---

### Шаг 4. Дать доступ к папке

1. Откройте Google Диск в браузере
2. Создайте папку (например: `Uploads`)
3. Правый клик → **Share**
4. Вставьте email сервис-аккаунта
   (`java-rush@javarush-487913.iam.gserviceaccount.com`)
5. Дайте роль **Editor**

Теперь Service Account может загружать файлы в эту папку.

---

### Шаг 5. Узнать ID папки

Откройте папку в браузере.

В адресной строке будет:

```
https://drive.google.com/drive/folders/1AbCDefGhIJKlMNop
```

Вот эта часть — и есть **Folder ID**:

```
1AbCDefGhIJKlMNop
```

---

### Шаг 6. Установить Python-библиотеку

```bash
pip install google-api-python-client google-auth

pip freeze > requirements.txt
```

---

### Шаг 7. Код загрузки в конкретную папку

```python
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SERVICE_ACCOUNT_FILE = 'service_account.json'
SCOPES = ['https://www.googleapis.com/auth/drive']

FOLDER_ID = 'ВАШ_ID_ПАПКИ'

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=SCOPES
)

service = build('drive', 'v3', credentials=credentials)

file_metadata = {
    'name': 'example.txt',
    'parents': [FOLDER_ID]
}

media = MediaFileUpload('example.txt', resumable=True)

file = service.files().create(
    body=file_metadata,
    media_body=media,
    fields='id'
).execute()

print('File ID:', file.get('id'))
```

---

#### Что происходит в коде

* Авторизация через Service Account
* Указание `parents` → это папка назначения
* Файл загружается напрямую без браузера

---

#### Результат

Файл появится в папке `Uploads` на вашем Google Диске.

---

#### Возможные ошибки

* `403 insufficient permissions`
  * → Вы забыли расшарить папку на email Service Account
* `File not found`
  * → Неверный ID папки
* `Drive API not enabled`
  * → Нужно включить Google Drive API в проекте

