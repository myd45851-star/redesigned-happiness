from getpass import getpass
from pathlib import Path
import secrets

path = Path(__file__).with_name('.env')
print('\nإعداد حساب الأدمن — يتم حفظ البيانات على جهازك داخل ملف .env فقط.')
name = input('اسم دخول الأدمن (مثلاً admin): ').strip()
while len(name) < 3:
    print('الاسم يجب أن يكون 3 أحرف على الأقل.')
    name = input('اسم دخول الأدمن: ').strip()
while True:
    password = getpass('كلمة مرور قوية (12 حرفًا على الأقل): ')
    if len(password) < 12:
        print('استخدم 12 حرفًا على الأقل.')
        continue
    confirm = getpass('أعد كتابة كلمة المرور: ')
    if password != confirm:
        print('كلمتا المرور غير متطابقتين.')
        continue
    break

def env_escape(value):
    return value.replace('\\', '\\\\').replace('"', '\\"')
content = '\n'.join([
    f'SECRET_KEY={secrets.token_urlsafe(48)}',
    f'ADMIN_NAME="{env_escape(name)}"',
    f'ADMIN_PASSWORD="{env_escape(password)}"',
    'DATABASE_URL=sqlite:///portal.db',
    'UPLOAD_FOLDER=private_uploads',
    ''
])
path.write_text(content, encoding='utf-8')
print('\nتم إنشاء إعدادات الأدمن بنجاح. احتفظ بملف .env ولا تشاركه مع أحد.')
