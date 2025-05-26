@echo off
chcp 65001 >nul
SETLOCAL EnableDelayedExpansion

echo ===================================================
echo      HE THONG QUAN LY DANH MUC DAU TU
echo ===================================================
echo.

echo [1/5] Kiem tra Python...
python --version 2>&1 | findstr "Python 3" >nul
if errorlevel 1 (
    echo ❌ LOI: Can Python 3!
    pause
    exit /b 1
)
echo ✅ Python OK!
echo.

echo [2/5] Vao thu muc src...
if not exist src (
    echo ❌ LOI: Khong tim thay thu muc src!
    pause
    exit /b 1
)
cd src
echo ✅ Da vao thu muc src
echo.

echo [3/5] Cai dat cac thu vien...
echo Dang cai dat requirements.txt...
pip install -r ../requirements.txt --user --quiet
if errorlevel 1 (
    echo ❌ LOI: Khong the cai dat requirements!
    echo Thu chay lenh sau de kiem tra:
    echo pip install -r ../requirements.txt
    pause
    exit /b 1
)
echo ✅ Da cai dat thanh cong!
echo.

echo [4/5] Chuan bi database...
echo Tao migrations...
python manage.py makemigrations
if errorlevel 1 (
    echo ❌ LOI: Khong the tao migrations!
    pause
    exit /b 1
)

echo Ap dung migrations...
python manage.py migrate
if errorlevel 1 (
    echo ❌ LOI: Khong the ap dung migrations!
    echo Kiem tra cau hinh database trong settings.py
    pause
    exit /b 1
)
echo ✅ Database da san sang!
echo.

echo [5/5] Tao admin account...
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@example.com', 'admin123') if not User.objects.filter(username='admin').exists() else print('✅ Admin account da co san')" 2>nul
echo.

echo ===================================================
echo              🎉 THANH CONG! 🎉
echo ===================================================
echo   URL chinh: http://127.0.0.1:8000
echo   Admin:     http://127.0.0.1:8000/admin
echo   
echo   👤 Username: admin
echo   🔑 Password: admin
echo ===================================================
echo.

echo Mo browser...
timeout /t 2 /nobreak >nul
start http://127.0.0.1:8000 2>nul

echo 🚀 Dang khoi dong server...
echo Nhan Ctrl+C de dung server
echo.
python manage.py runserver

ENDLOCAL 