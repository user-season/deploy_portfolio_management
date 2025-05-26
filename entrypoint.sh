#!/bin/bash

# Exit on any error
set -e

echo "=== CHECK PYTHON VERSION ==="
if ! python --version 2>&1 | grep -q "Python 3"; then
    echo "ERROR: Python3 is required!"
    exit 1
fi
echo "=== PYTHON VERSION CHECKED ==="

echo "=== LOAD ENVIRONMENT VARIABLES ==="
if [ -f .env ]; then
    export $(grep -v '^#' .env | grep -E '^[A-Za-z_][A-Za-z0-9_]*=.*$' | sed 's/[[:space:]]*$//' | xargs)
else
    echo "WARNING: .env file not found, using default Docker environment variables"
fi

# Force override with Docker environment variables (prioritize Docker values)
export DATABASE_NAME=portfolio_management
export DATABASE_USER=postgres
export DATABASE_PASSWORD=postgres123
export DATABASE_HOST=db
export DATABASE_PORT=5432
export admin_username=admin
export admin_password=admin123

echo "Database config: HOST=$DATABASE_HOST, PORT=$DATABASE_PORT, USER=$DATABASE_USER, DB=$DATABASE_NAME"
echo "=== LOAD ENVIRONMENT VARIABLES COMPLETELY ==="

echo "=== WAIT FOR DATABASE ==="
until pg_isready -h $DATABASE_HOST -p $DATABASE_PORT -U $DATABASE_USER; do
    echo "Database is not ready yet, waiting..."
    sleep 2
done
echo "=== DATABASE IS AVAILABLE ==="

echo "=== CONNECT TO DATABASE ==="
export PGPASSWORD="$DATABASE_PASSWORD"
psql -h "$DATABASE_HOST" -U "$DATABASE_USER" -p "$DATABASE_PORT" -c "SELECT 1;" >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "ERROR: Cannot connect to PostgreSQL!"
    echo "Check PostgreSQL server and sign-in information!"
    exit 1
fi
echo "=== DATABASE IS READY ==="

echo "=== UPDATE METADATA OF DATABASE ==="
psql -h "$DATABASE_HOST" -U "$DATABASE_USER" -p "$DATABASE_PORT" -c "ALTER DATABASE $DATABASE_NAME REFRESH COLLATION VERSION;"
echo "=== UPDATE METADATA OF DATABASE COMPLETELY ==="

echo "=== CREATE VIRTUAL ENVIRONMENT ==="
python -m venv venv || { echo "❌ Failed to create venv"; exit 1; }
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    if [ -f "requirements.txt" ]; then
        pip install --upgrade pip
        pip install wheel setuptools
        echo "📦 Installing dependencies from requirements.txt..."
        pip install --upgrade pip
        pip install -r requirements.txt || { echo "❌ Failed to install requirements."; exit 1; }
    else
        echo "⚠️  requirements.txt not found. Skipping dependency installation."
    fi
else
    echo "❌ Activate script not found! venv creation may have failed."
    exit 1
fi
echo "=== VIRTUAL ENVIRONMENT ACTIVATED ==="

if [ ! -d src ]; then
    echo "ERROR: src directory not found!"
    exit 1
fi

echo "=== NAVIGATE TO PROJECT DIRECTORY ==="
rm -rf /app/staticfiles
# python manage.py collectstatic --noinput
cd /app/src
mkdir -p static
mkdir -p media

echo "=== CREATE DATABASE ==="
psql -h "$DATABASE_HOST" -U "$DATABASE_USER" -p "$DATABASE_PORT" -c "DROP DATABASE IF EXISTS $DATABASE_NAME;"
psql -h "$DATABASE_HOST" -U "$DATABASE_USER" -p "$DATABASE_PORT" -c "CREATE DATABASE $DATABASE_NAME WITH ENCODING='UTF8' TEMPLATE=template0;"
echo "=== CREATE DATABASE COMPLETELY ==="

echo "=== CREATE MIGRATIONS ==="
rm -rf portfolio/migrations
mkdir -p portfolio/migrations
touch portfolio/migrations/__init__.py
python manage.py makemigrations
if [ $? -ne 0 ]; then
    echo "ERROR: Cannot create migrations"
    exit 1
fi
python manage.py migrate
if [ $? -ne 0 ]; then
    echo "ERROR: Cannot apply migrations"
    echo "Check PostgreSQL connection"
    exit 1
fi
echo "=== CREATE MIGRATIONS COMPLETELY ==="

echo "=== CREATE ADMIN ACCOUNT ==="
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('$admin_username', 'admin@example.com', '$admin_password') if not User.objects.filter(username='$admin_username').exists() else print('Admin already exists!!!')"
echo "=== CREATE ADMIN ACCOUNT COMPLETELY ==="

echo "=== RUN SERVER ==="
exec "$@"