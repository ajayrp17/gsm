# How to Run the Application

This project is a Django-based Online Grocery Delivery System.

## Prerequisites

- Python 3.x
- `pip`
- Optional: MySQL server if you do not want to use SQLite

## 1. Open the project folder

```powershell
cd "c:\Users\ajayr\Downloads\finalyr\New folder (2)\gsm"
```

## 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Command Prompt:

```cmd
python -m venv .venv
.venv\Scripts\activate
```

## 3. Install dependencies

```powershell
pip install -r requirements.txt
```

## 4. Choose the database

### Option A: Run with SQLite

No extra setup is required. SQLite is the default.

### Option B: Run with MySQL

Set these environment variables before starting the server:

```powershell
$env:USE_MYSQL="1"
$env:MYSQL_DATABASE="grocery_delivery"
$env:MYSQL_USER="root"
$env:MYSQL_PASSWORD="your_password"
$env:MYSQL_HOST="127.0.0.1"
$env:MYSQL_PORT="3306"
```

If you want custom Django settings too:

```powershell
$env:DJANGO_SECRET_KEY="replace-me"
$env:DJANGO_DEBUG="1"
$env:DJANGO_ALLOWED_HOSTS="127.0.0.1,localhost"
```

Note: `.env.example` is a reference file. This project reads environment variables directly, so copying that file alone will not apply settings unless you load them into your shell.

## 5. Apply migrations

```powershell
python manage.py migrate
```

## 6. Load sample data

```powershell
python manage.py seed_data
```

This creates:

- Admin user: `admin / admin123`
- Demo user: `demo_user / demo12345`

## 7. Start the server

```powershell
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

## Useful pages

- Home: `http://127.0.0.1:8000/`
- Login: `http://127.0.0.1:8000/accounts/login/`
- Dashboard: `http://127.0.0.1:8000/dashboard/`

## Common commands

Create new migrations if models change:

```powershell
python manage.py makemigrations
python manage.py migrate
```

Load fixture instead of seeded data:

```powershell
python manage.py loaddata catalog/fixtures/sample_data.json
```

Create your own admin user:

```powershell
python manage.py createsuperuser
```

## Common issues

### `mysqlclient` install fails

Use SQLite first. It works without MySQL configuration.

### Static or media files are not showing

Run the app with `DJANGO_DEBUG=1` in development. The project serves static and media files automatically in debug mode.

### Virtual environment activation is blocked in PowerShell

Run PowerShell as a user shell and allow script execution for the current session:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```
