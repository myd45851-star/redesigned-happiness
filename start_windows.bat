@echo off
setlocal
cd /d "%~dp0"
title بوابة هندسة الزراعة والحيوية - الإعداد والتشغيل

echo ================================================
echo   بوابة مواد هندسة الزراعة والحيوية
echo   إعداد أول مرة ثم تشغيل الموقع محليًا
echo ================================================
echo.
where py >nul 2>nul
if errorlevel 1 (
  echo لم يتم العثور على Python Launcher.
  echo ثبّت Python 3.12 أو 3.13 من python.org مع تفعيل Add Python to PATH.
  pause
  exit /b 1
)
py -3.13 --version >nul 2>nul
if errorlevel 1 (
  py -3.12 --version >nul 2>nul
  if errorlevel 1 (
    echo لم أجد Python 3.12 أو 3.13.
    echo قد لا تكون كل المكتبات متوافقة مع Python 3.15 بعد.
    echo ثبّت Python 3.12 أو 3.13 ثم أعد تشغيل هذا الملف.
    pause
    exit /b 1
  ) else (
    set PYTHON_CMD=py -3.12
  )
) else (
  set PYTHON_CMD=py -3.13
)
if not exist ".venv\Scripts\python.exe" (
  echo [1/3] إنشاء بيئة Python...
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 goto failed
)
echo [2/3] تثبيت مكتبات الموقع وتحديثها...
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failed
if not exist ".env" (
  echo [3/3] إنشاء بيانات الأدمن لأول مرة.
  .venv\Scripts\python.exe setup_admin.py
  if errorlevel 1 goto failed
) else (
  echo تم العثور على ملف الإعدادات .env، سيتم استخدامه.
)
echo.
echo جاري تشغيل الموقع...
echo افتح المتصفح على: http://127.0.0.1:8000
echo لإيقاف الموقع اضغط Ctrl+C في هذه النافذة.
echo.
.venv\Scripts\waitress-serve.exe --host=127.0.0.1 --port=8000 app:app
pause
exit /b 0
:failed
echo حدث خطأ أثناء الإعداد. صوّر الرسالة وأرسلها للمساعدة.
pause
exit /b 1
