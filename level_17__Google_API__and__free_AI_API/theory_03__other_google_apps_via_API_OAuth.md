Через OAuth 2.0 можно подключаться практически ко всем пользовательским сервисам Google.  
Ниже — структурированный список основных Google-приложений с:

* названием API
* примерами `scope`
* что нужно дополнительно подключить к проекту в **Google Cloud Console**

---

### 1. Google Sheets

API: Google Sheets API

### Включить в проекте:

`APIs & Services → Library → Google Sheets API → Enable`

### Основные scopes:

```text
https://www.googleapis.com/auth/spreadsheets
https://www.googleapis.com/auth/spreadsheets.readonly
```

---

### 2. Google Docs

API: Google Docs API

### Включить:

`Google Docs API`

### Scopes:

```text
https://www.googleapis.com/auth/documents
https://www.googleapis.com/auth/documents.readonly
```

---

### 3. Google Drive

API: Google Drive API

### Включить:

`Google Drive API`

### Scopes:

```text
https://www.googleapis.com/auth/drive
https://www.googleapis.com/auth/drive.file
https://www.googleapis.com/auth/drive.readonly
```

---

### 4. Gmail

API: Gmail API

### Включить:

`Gmail API`

### Scopes:

```text
https://www.googleapis.com/auth/gmail.send
https://www.googleapis.com/auth/gmail.readonly
https://www.googleapis.com/auth/gmail.modify
https://mail.google.com/   # полный доступ
```

---

### 5. Google Calendar

API: Google Calendar API

### Включить:

`Google Calendar API`

### Scopes:

```text
https://www.googleapis.com/auth/calendar
https://www.googleapis.com/auth/calendar.readonly
https://www.googleapis.com/auth/calendar.events
```

---

### 6. Google Contacts

API: People API

(Контакты теперь работают через People API)

### Включить:

`People API`

### Scopes:

```text
https://www.googleapis.com/auth/contacts
https://www.googleapis.com/auth/contacts.readonly
```

---

### 7. Google People (профиль пользователя)

API: People API

### Включить:

`People API`

### Scopes:

```text
https://www.googleapis.com/auth/userinfo.profile
https://www.googleapis.com/auth/userinfo.email
openid
```

---

### 8. Google Forms

API: Google Forms API

### Включить:

`Google Forms API`

### Scopes:

```text
https://www.googleapis.com/auth/forms.body
https://www.googleapis.com/auth/forms.responses.readonly
```

---

### 9. Google Slides

API: Google Slides API

### Включить:

`Google Slides API`

### Scopes:

```text
https://www.googleapis.com/auth/presentations
https://www.googleapis.com/auth/presentations.readonly
```

---

### 10. Google Tasks

API: Google Tasks API

### Включить:

`Google Tasks API`

### Scopes:

```text
https://www.googleapis.com/auth/tasks
https://www.googleapis.com/auth/tasks.readonly
```

