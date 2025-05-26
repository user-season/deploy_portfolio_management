@echo off
SETLOCAL EnableDelayedExpansion

echo === KIEM TRA PHIEN BAN PYTHON ===
python --version 2>&1 | findstr "Python 3" >nul
if errorlevel 1 (
    echo LOI: Can Python 3 de chay ung dung!
    pause
    exit /b 1
)
echo === DA KIEM TRA PHIEN BAN PYTHON ===

echo === THIET LAP BIEN MOI TRUONG ===
rem Cau hinh Database - Da cap nhat theo file .env cua ban
set DATABASE_NAME=db_for_pm
set DATABASE_USER=postgres
set DATABASE_PASSWORD=admin123
set DATABASE_HOST=localhost
set DATABASE_PORT=5432

rem Cau hinh tai khoan Admin
set admin_username=admin
set admin_password=admin123

rem Cau hinh Django
set DEBUG=False
set SECRET_KEY=django-insecure-default-key-for-development
set ALLOWED_HOSTS=localhost,127.0.0.1,*

rem Doc tu file .env neu co, se ghi de cac gia tri mac dinh o tren
if exist .env (
    echo Dang tai cau hinh tu file .env...
    for /f "usebackq tokens=1,* delims==" %%A in (.env) do (
        rem Bo qua cac dong bat dau bang # hoac dong trong
        echo %%A | findstr /b /r /c:"#.*" >nul
        if errorlevel 1 (
            if not "%%A"=="" (
                rem Loai bo khoang trang va dau ngoac kep thua
                set "%%A=%%B"
            )
        )
    )
    echo Da tai cau hinh tu file .env thanh cong!
) else (
    echo Khong tim thay file .env, su dung cau hinh mac dinh...
)
echo === DA THIET LAP BIEN MOI TRUONG ===

echo === KIEM TRA POSTGRESQL ===
psql --version >nul 2>&1
if errorlevel 1 (
    echo LOI: PostgreSQL chua duoc cai dat hoac khong co trong PATH!
    echo Vui long cai dat PostgreSQL va dam bao lenh psql co the su dung duoc.
    pause
    exit /b 1
)
echo === DA CAI DAT POSTGRESQL ===

echo === KET NOI DEN DATABASE ===
set PGPASSWORD=!DATABASE_PASSWORD!
echo Dang thu ket noi voi user: !DATABASE_USER!
echo Host: !DATABASE_HOST!:!DATABASE_PORT!
psql -h !DATABASE_HOST! -p !DATABASE_PORT! -U !DATABASE_USER! -d postgres -c "SELECT 1;" >nul 2>&1
if errorlevel 1 (
    echo LOI: Khong the ket noi den PostgreSQL!
    echo Vui long kiem tra:
    echo - PostgreSQL server dang chay
    echo - Thong tin dang nhap dung (User: !DATABASE_USER!)
    echo - Mat khau: !DATABASE_PASSWORD!
    echo - Host co the truy cap duoc: !DATABASE_HOST!:!DATABASE_PORT!
    echo.
    echo Goi y: Thu chay lenh sau de kiem tra:
    echo psql -h !DATABASE_HOST! -U !DATABASE_USER! -d postgres
    pause
    exit /b 1
)
echo === KET NOI DATABASE THANH CONG ===

echo === CAP NHAT METADATA CUA DATABASE ===
psql -h !DATABASE_HOST! -p !DATABASE_PORT! -U !DATABASE_USER! -d !DATABASE_NAME! -c "ALTER DATABASE !DATABASE_NAME! REFRESH COLLATION VERSION;" 2>nul
echo === DA CAP NHAT METADATA CUA DATABASE ===

echo === TAO MOI TRUONG AO (VIRTUAL ENVIRONMENT) ===
if exist venv (
    echo Dang xoa moi truong ao cu...
    rmdir /s /q venv
    timeout /t 2 /nobreak >nul
)
echo Dang tao moi truong ao moi...
python -m venv venv
if errorlevel 1 (
    echo LOI: Khong the tao moi truong ao!
    pause
    exit /b 1
)

echo Dang kich hoat moi truong ao...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo LOI: Khong the kich hoat moi truong ao!
    pause
    exit /b 1
)

echo Dang nang cap pip va cai dat cac goi co ban...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo LOI: Khong the nang cap pip!
    pause
    exit /b 1
)

python -m pip install wheel setuptools
if errorlevel 1 (
    echo LOI: Khong the cai dat wheel va setuptools!
    pause
    exit /b 1
)

if not exist requirements.txt (
    echo LOI: Khong tim thay file requirements.txt!
    pause
    exit /b 1
)

echo Dang cai dat cac thu vien phu thuoc cua du an...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo LOI: Khong the cai dat cac thu vien tu requirements.txt!
    pause
    exit /b 1
)
echo === DA TAO MOI TRUONG AO THANH CONG ===

if not exist src (
    echo LOI: Khong tim thay thu muc src!
    pause
    exit /b 1
)
cd src

echo === CHUAN BI CAC THU MUC ===
if not exist static mkdir static
if not exist media mkdir media
echo === DA CHUAN BI CAC THU MUC ===

echo === TAO DATABASE ===
set PGPASSWORD=!DATABASE_PASSWORD!
echo Dang xoa database cu (neu co): !DATABASE_NAME!
psql -h !DATABASE_HOST! -p !DATABASE_PORT! -U !DATABASE_USER! -d postgres -c "DROP DATABASE IF EXISTS !DATABASE_NAME!;" >nul 2>&1
echo Dang tao database moi: !DATABASE_NAME!
psql -h !DATABASE_HOST! -p !DATABASE_PORT! -U !DATABASE_USER! -d postgres -c "CREATE DATABASE !DATABASE_NAME! WITH ENCODING='UTF8' TEMPLATE=template0;" >nul 2>&1
if errorlevel 1 (
    echo LOI: Khong the tao database !DATABASE_NAME!
    echo Vui long kiem tra:
    echo - User PostgreSQL '!DATABASE_USER!' co quyen CREATE DATABASE
    echo - Ten database '!DATABASE_NAME!' hop le
    pause
    exit /b 1
)
echo === DA TAO DATABASE '!DATABASE_NAME!' THANH CONG ===

echo === TAO MIGRATIONS ===
if exist portfolio\migrations (
    echo Dang xoa migrations cu...
    rmdir /s /q portfolio\migrations
)
mkdir portfolio\migrations
echo. > portfolio\migrations\__init__.py

echo Dang tao migrations moi...
python manage.py makemigrations
if errorlevel 1 (
    echo LOI: Khong the tao migrations
    pause
    exit /b 1
)

echo Dang ap dung migrations vao database...
python manage.py migrate
if errorlevel 1 (
    echo LOI: Khong the ap dung migrations
    echo Kiem tra ket noi PostgreSQL va quyen truy cap database
    pause
    exit /b 1
)
echo === DA HOAN THANH MIGRATIONS ===

echo === TAO TAI KHOAN ADMIN ===
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('!admin_username!', 'admin@example.com', '!admin_password!') if not User.objects.filter(username='!admin_username!').exists() else print('Tai khoan admin da ton tai')"
if errorlevel 1 (
    echo CANH BAO: Khong the tao tai khoan admin, nhung van tiep tuc...
) else (
    echo Da tao tai khoan admin thanh cong!
)
echo === DA THIET LAP TAI KHOAN ADMIN ===

echo === KHOI DONG SERVER PHAT TRIEN ===
echo Dang mo trinh duyet...
start http://127.0.0.1:8000 || echo CANH BAO: Khong the tu dong mo trinh duyet
echo.
echo ================================================
echo     He Thong Quan Ly Danh Muc Dau Tu da san sang!
echo ================================================
echo  URL chinh: http://127.0.0.1:8000
echo  Trang quan tri: http://127.0.0.1:8000/admin
echo  
echo  Database: !DATABASE_NAME!
echo  Ten dang nhap Admin: !admin_username!
echo  Mat khau Admin: !admin_password!
echo  
echo  Che do DEBUG: !DEBUG!
echo ================================================
echo.
echo Nhan Ctrl+C de dung server...
echo.
python manage.py runserver

ENDLOCAL