@echo off
py -m venv .venv
call .venv\Scripts\activate
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
echo.
echo قبل التشغيل: اضبط ADMIN_NAME و ADMIN_PASSWORD و SECRET_KEY كمتغيرات بيئة.
echo ثم شغّل: waitress-serve --host=127.0.0.1 --port=8000 app:app
pause
