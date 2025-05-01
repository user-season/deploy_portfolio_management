@echo off
SETLOCAL EnableDelayedExpansion

echo === Kiem tra PostgreSQL ===
psql --version > nul 2>&1
if errorlevel 1 (
    echo Loi: PostgreSQL chua duoc cai dat hoac chua duoc them vao PATH
    echo Vui long cai dat PostgreSQL va dam bao no duoc them vao PATH
    pause
    exit /b 1
)

REM Kiem tra ket noi PostgreSQL truoc khi tiep tuc
echo === Kiem tra ket noi PostgreSQL ===
set PGPASSWORD=admin123
psql -U postgres -c "SELECT 1;" > nul 2>&1
if errorlevel 1 (
    echo Loi: Khong the ket noi toi PostgreSQL server
    echo Vui long kiem tra lai server PostgreSQL va thong tin dang nhap
    pause
    exit /b 1
)

echo === Khoi tao moi truong ===

REM Xoa moi truong ao cu neu ton tai
if exist venv (
    rmdir /s /q venv
    timeout /t 2 /nobreak >nul
)

REM Tao va kich hoat moi truong ao moi
python -m venv venv
call venv\Scripts\activate.bat

REM Cap nhat pip va cai dat cac goi co ban
python -m pip install --upgrade pip
python -m pip install wheel setuptools

REM Cai dat cac goi tu requirements.txt
python -m pip install -r requirements.txt

REM Di chuyen vao thu muc src
cd src

REM Xoa database cu neu co
if exist db.sqlite3 (
    del db.sqlite3
)

@REM REM Tao cac thu muc can thiet
@REM if not exist static mkdir static
@REM if not exist media mkdir media
@REM if not exist ..\data\stock_data mkdir ..\data\stock_data


REM Tao database PostgreSQL
echo === Tao database PostgreSQL ===
set PGPASSWORD=admin123
psql -U postgres -c "DROP DATABASE IF EXISTS db_for_pm;"
psql -U postgres -c "CREATE DATABASE db_for_pm WITH ENCODING='UTF8' TEMPLATE=template0;"

REM Xoa migrations cu
rmdir /s /q portfolio\migrations
mkdir portfolio\migrations
type nul > portfolio\migrations\__init__.py

REM Tao migrations moi va ap dung
python manage.py makemigrations
if errorlevel 1 (
    echo Loi: Khong the tao migrations
    pause
    exit /b 1
)

python manage.py migrate
if errorlevel 1 (
    echo Loi: Khong the ap dung migrations
    echo Kiem tra lai ket noi PostgreSQL
    pause
    exit /b 1
)

REM Tao superuser
echo.
echo === Tao tai khoan admin ===
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@example.com', 'admin123') if not User.objects.filter(username='admin').exists() else print('Admin da ton tai')"

REM Mo trinh duyet
start http://127.0.0.1:8000

REM Chay server
echo === Khoi dong server ===
python manage.py runserver

ENDLOCAL