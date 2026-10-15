import os, secrets
from datetime import datetime
from functools import wraps
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, flash, request, send_from_directory, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Length, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///portal.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = os.path.abspath(os.environ.get("UPLOAD_FOLDER", "private_uploads"))
ALLOWED_EXTENSIONS = {"pdf", "ppt", "pptx", "doc", "docx", "xls", "xlsx", "zip", "rar", "jpg", "jpeg", "png", "mp4"}
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "سجّل الدخول أولًا للوصول إلى المحتوى."
csrf = CSRFProtect(app)

TRACKS = {
    "irrigation": "هندسة الري والصرف الحقلي",
    "biosystems": "هندسة النظم الحيوية",
    "machines": "هندسة الآلات والقوى الزراعية",
    "general": "الهندسة الزراعية العامة",
}
KINDS = {"lecture": "محاضرات", "section": "سكاشن"}

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    approved = db.Column(db.Boolean, default=False, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(140), nullable=False)
    track = db.Column(db.String(30), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint("name", "track", name="unique_subject_per_track"),)

class Material(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subject.id"), nullable=False)
    kind = db.Column(db.String(20), nullable=False)
    slot = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(160), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    stored_name = db.Column(db.String(255), nullable=False, unique=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    subject = db.relationship("Subject", backref=db.backref("materials", lazy=True, cascade="all, delete-orphan"))
    __table_args__ = (db.UniqueConstraint("subject_id", "kind", "slot", name="unique_material_slot"),)

class EmptyForm(FlaskForm):
    submit = SubmitField("حفظ")

class RegisterForm(FlaskForm):
    name = StringField("اسم الطالب (اسم فريد لتسجيل الدخول)", validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField("كلمة المرور", validators=[DataRequired(), Length(min=10, max=128)])
    confirm = PasswordField("تأكيد كلمة المرور", validators=[DataRequired(), EqualTo("password", message="كلمتا المرور غير متطابقتين.")])
    submit = SubmitField("إرسال طلب التسجيل")

class LoginForm(FlaskForm):
    name = StringField("اسم الطالب", validators=[DataRequired(), Length(max=80)])
    password = PasswordField("كلمة المرور", validators=[DataRequired()])
    submit = SubmitField("تسجيل الدخول")

class SubjectForm(FlaskForm):
    track = SelectField("التوجه", choices=[(k,v) for k,v in TRACKS.items()], validators=[DataRequired()])
    name = StringField("اسم المادة", validators=[DataRequired(), Length(min=2, max=140)])
    submit = SubmitField("إضافة المادة")

class UploadForm(FlaskForm):
    kind = SelectField("نوع المحتوى", choices=[(k,v) for k,v in KINDS.items()], validators=[DataRequired()])
    slot = SelectField("الخانة", choices=[(str(i), f"الخانة {i:02d}") for i in range(1,12)], validators=[DataRequired()])
    title = StringField("عنوان الملف", validators=[DataRequired(), Length(min=2, max=160)])
    submit = SubmitField("رفع الملف")

@login_manager.user_loader
def load_user(user_id): return db.session.get(User, int(user_id))

def admin_required(fn):
    @wraps(fn)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return fn(*args, **kwargs)
    return wrapped

def approved_required(fn):
    @wraps(fn)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin and not current_user.approved:
            logout_user()
            flash("حسابك ما زال بانتظار موافقة الإدارة.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapped

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.context_processor
def inject_globals():
    return {"TRACKS": TRACKS, "KINDS": KINDS}

@app.route("/")
def index():
    if current_user.is_authenticated:
        if current_user.is_admin: return redirect(url_for("admin_dashboard"))
        if current_user.approved: return redirect(url_for("library"))
    return render_template("landing.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        name = form.name.data.strip()
        if User.query.filter_by(name=name).first():
            flash("هذا الاسم مستخدم بالفعل. أضف اسمًا مميزًا أو جزءًا من اسمك.", "danger")
        else:
            user = User(name=name, approved=False, is_admin=False)
            user.set_password(form.password.data)
            db.session.add(user); db.session.commit()
            flash("تم إرسال طلبك. لن تتمكن من دخول المكتبة قبل موافقة الأدمن.", "success")
            return redirect(url_for("login"))
    return render_template("register.html", form=form)

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(name=form.name.data.strip()).first()
        if user and user.check_password(form.password.data):
            if not user.is_admin and not user.approved:
                flash("طلبك قيد المراجعة. انتظر موافقة الأدمن.", "warning")
            else:
                login_user(user)
                return redirect(url_for("admin_dashboard" if user.is_admin else "library"))
        else:
            flash("بيانات الدخول غير صحيحة.", "danger")
    return render_template("login.html", form=form)

@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("تم تسجيل الخروج.", "info")
    return redirect(url_for("index"))

@app.route("/library")
@approved_required
def library():
    subjects = Subject.query.order_by(Subject.track, Subject.name).all()
    return render_template("library.html", subjects=subjects)

@app.route("/subject/<int:subject_id>", methods=["GET", "POST"])
@approved_required
def subject_detail(subject_id):
    subject = db.get_or_404(Subject, subject_id)
    form = UploadForm()
    if current_user.is_admin and form.validate_on_submit():
        upload = request.files.get("file")
        if not upload or not upload.filename:
            flash("اختر ملفًا أولًا.", "danger")
        elif not allowed_file(upload.filename):
            flash("نوع الملف غير مسموح. الأنواع المسموحة موضحة أسفل النموذج.", "danger")
        else:
            kind, slot = form.kind.data, int(form.slot.data)
            old = Material.query.filter_by(subject_id=subject.id, kind=kind, slot=slot).first()
            if old:
                try: os.remove(os.path.join(app.config["UPLOAD_FOLDER"], old.stored_name))
                except OSError: pass
                db.session.delete(old)
            safe = secure_filename(upload.filename)
            stored = secrets.token_hex(16) + "_" + safe
            upload.save(os.path.join(app.config["UPLOAD_FOLDER"], stored))
            material = Material(subject_id=subject.id, kind=kind, slot=slot,
                                title=form.title.data.strip(), original_name=safe, stored_name=stored)
            db.session.add(material); db.session.commit()
            flash("تم رفع الملف بنجاح.", "success")
            return redirect(url_for("subject_detail", subject_id=subject.id))
    materials = {(m.kind, m.slot): m for m in subject.materials}
    return render_template("subject.html", subject=subject, form=form, materials=materials)

@app.route("/download/<int:material_id>")
@approved_required
def download(material_id):
    material = db.get_or_404(Material, material_id)
    return send_from_directory(app.config["UPLOAD_FOLDER"], material.stored_name,
                               as_attachment=True, download_name=material.original_name)

@app.route("/admin")
@admin_required
def admin_dashboard():
    pending = User.query.filter_by(approved=False, is_admin=False).order_by(User.created_at).all()
    students = User.query.filter_by(is_admin=False).order_by(User.name).all()
    subjects = Subject.query.order_by(Subject.track, Subject.name).all()
    return render_template("admin.html", pending=pending, students=students, subjects=subjects, form=SubjectForm())

@app.route("/admin/user/<int:user_id>/<action>", methods=["POST"])
@admin_required
def manage_user(user_id, action):
    user = db.get_or_404(User, user_id)
    if user.is_admin: abort(400)
    if action == "approve":
        user.approved = True
        flash(f"تمت الموافقة على حساب {user.name}.", "success")
    elif action == "reject":
        db.session.delete(user)
        flash("تم رفض الطلب وحذف الحساب.", "info")
    elif action == "revoke":
        user.approved = False
        flash("تم إيقاف اعتماد الحساب.", "warning")
    else: abort(400)
    db.session.commit()
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/subject/add", methods=["POST"])
@admin_required
def add_subject():
    form = SubjectForm()
    if form.validate_on_submit():
        subject = Subject(name=form.name.data.strip(), track=form.track.data)
        db.session.add(subject)
        try:
            db.session.commit(); flash("تمت إضافة المادة.", "success")
        except Exception:
            db.session.rollback(); flash("المادة موجودة بالفعل في هذا التوجه.", "danger")
    else:
        flash("تحقق من اسم المادة والتوجه.", "danger")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/subject/<int:subject_id>/delete", methods=["POST"])
@admin_required
def delete_subject(subject_id):
    subject = db.get_or_404(Subject, subject_id)
    for m in subject.materials:
        try: os.remove(os.path.join(app.config["UPLOAD_FOLDER"], m.stored_name))
        except OSError: pass
    db.session.delete(subject); db.session.commit()
    flash("تم حذف المادة وملفاتها.", "info")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/material/<int:material_id>/delete", methods=["POST"])
@admin_required
def delete_material(material_id):
    material = db.get_or_404(Material, material_id)
    sid = material.subject_id
    try: os.remove(os.path.join(app.config["UPLOAD_FOLDER"], material.stored_name))
    except OSError: pass
    db.session.delete(material); db.session.commit()
    flash("تم حذف الملف.", "info")
    return redirect(url_for("subject_detail", subject_id=sid))

@app.errorhandler(403)
def forbidden(e): return render_template("error.html", code=403, message="ليس لديك صلاحية للوصول إلى هذه الصفحة."), 403
@app.errorhandler(413)
def too_large(e): return render_template("error.html", code=413, message="حجم الملف أكبر من الحد المسموح (50 ميجابايت)."), 413

with app.app_context():
    db.create_all()
    admin_name = os.environ.get("ADMIN_NAME")
    admin_password = os.environ.get("ADMIN_PASSWORD")
    if admin_name and admin_password and not User.query.filter_by(is_admin=True).first():
        admin = User(name=admin_name.strip(), is_admin=True, approved=True)
        admin.set_password(admin_password)
        db.session.add(admin); db.session.commit()

if __name__ == "__main__":
    app.run(debug=False)
