#!/bin/bash

# Exit on any error
set -e

echo "=== LOAD ENVIRONMENT VARIABLES ==="
if [ -f .env ]; then
    export $(grep -v '^#' .env | grep -E '^[A-Za-z_][A-Za-z0-9_]*=.*$' | sed 's/[[:space:]]*$//' | xargs)
else
    echo "WARNING: .env file not found, relying on Docker environment variables"
fi
echo "=== LOAD ENVIRONMENT VARIABLES COMPLETELY ==="

echo "=== CHECK POSTGRES DATABASE ==="
if ! command -v psql >/dev/null 2>&1; then
    echo "ERROR: PostgreSQL client (psql) is not installed!"
    exit 1
fi
echo "=== POSTGRES DATABASE CLIENT IS INSTALLED ==="

echo "=== WAIT FOR DATABASE ==="
until pg_isready -h $DATABASE_HOST_DOCKER_COMPOSE -p $DATABASE_PORT -U $DATABASE_USER; do
    echo "Database is not ready yet, waiting..."
    sleep 2
done
echo "=== DATABASE IS AVAILABLE ==="

echo "=== CONNECT TO DATABASE ==="
export PGPASSWORD="$DATABASE_PASSWORD"
psql -h "$DATABASE_HOST_DOCKER_COMPOSE" -U "$DATABASE_USER" -p "$DATABASE_PORT" -c "SELECT 1;" >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "ERROR: Cannot connect to PostgreSQL!"
    echo "Check PostgreSQL server and sign-in information!"
    exit 1
fi
echo "=== DATABASE IS READY ==="

echo "=== UPDATE METADATA OF DATABASE ==="
psql -h "$DATABASE_HOST_DOCKER_COMPOSE" -U "$DATABASE_USER" -p "$DATABASE_PORT" -c "ALTER DATABASE $DATABASE_NAME REFRESH COLLATION VERSION;"
echo "=== UPDATE METADATA OF DATABASE COMPLETELY ==="

# echo "=== CREATE VIRTUAL ENVIRONMENT ==="
# python -m venv venv
# source /app/venv/bin/activate
# if ! python --version >/dev/null 2>&1; then
#     echo "ERROR: Failed to activate virtual environment!"
#     exit 1
# fi
# echo "=== VIRTUAL ENVIRONMENT ACTIVATED ==="

echo "=== NAVIGATE TO PROJECT DIRECTORY ==="
cd /app/src
mkdir -p static
mkdir -p media

echo "=== CREATE DATABASE ==="
psql -h "$DATABASE_HOST_DOCKER_COMPOSE" -U "$DATABASE_USER" -p "$DATABASE_PORT" -c "DROP DATABASE IF EXISTS $DATABASE_NAME;"
psql -h "$DATABASE_HOST_DOCKER_COMPOSE" -U "$DATABASE_USER" -p "$DATABASE_PORT" -c "CREATE DATABASE $DATABASE_NAME WITH ENCODING='UTF8' TEMPLATE=template0;"
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