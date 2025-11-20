import os, io, json, csv
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_file, make_response
from werkzeug.utils import secure_filename
from datetime import datetime, timezone
from models import db, User, Attendance, Admin
from utils import (
    allowed_file,
    get_face_encodings_from_image_file,
    get_face_encodings_from_pil_image,
    compare_face_to_user_encodings,
    load_all_known_users,
)
from PIL import Image
import base64
import numpy as np
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from werkzeug.security import generate_password_hash, check_password_hash


# --------------------------
# APP CONFIG
# --------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
KNOWN_DIR = os.path.join(BASE_DIR, 'known_faces')
os.makedirs(KNOWN_DIR, exist_ok=True)

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = KNOWN_DIR

db.init_app(app)


# --------------------------
# INITIALIZE DB
# --------------------------
with app.app_context():
    db.create_all()
    if Admin.query.count() == 0:
        print("Creating default admin user: admin/admin123")
        a = Admin(username="admin", password_hash=generate_password_hash("admin123"))
        db.session.add(a)
        db.session.commit()


# --------------------------
# AUTH DECORATOR
# --------------------------
def login_required(f):
    from functools import wraps

    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return wrapper


# --------------------------
# ROUTES
# --------------------------
@app.route('/')
def index():
    return render_template('index.html')


# ---------- ADMIN LOGIN ----------
@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()

        admin = Admin.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password_hash, password):
            session['admin_logged_in'] = True
            session['admin_username'] = admin.username
            flash("Logged in", "success")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid credentials", "danger")
            return redirect(url_for("login"))

    return render_template('login.html')


@app.route('/admin/logout')
def logout():
    session.pop("admin_logged_in", None)
    session.pop("admin_username", None)
    flash("Logged out", "info")
    return redirect(url_for("index"))


# ---------- ADMIN DASHBOARD ----------
@app.route('/admin')
@login_required
def admin_dashboard():
    users = User.query.order_by(User.name).all()

    user_data = []
    for u in users:
        try:
            enc_count = len(json.loads(u.encodings_json)) if u.encodings_json else 0
        except:
            enc_count = 0

        user_data.append({
            "id": u.id,
            "student_id": u.student_id,
            "name": u.name,
            "image_filename": u.image_filename,
            "enc_count": enc_count
        })

    return render_template('admin_dashboard.html', users=user_data)


# ---------- SINGLE IMAGE REGISTER ----------
@app.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    if request.method == "POST":
        student_id = request.form.get("student_id").strip()
        name = request.form.get("name").strip()
        file = request.files.get("image")

        if not student_id or not name or not file:
            flash("All fields are required", "danger")
            return redirect(url_for("register"))

        if not allowed_file(file.filename):
            flash("Only JPG/PNG allowed", "danger")
            return redirect(url_for("register"))

        filename = secure_filename(f"{student_id}_{file.filename}")
        filepath = os.path.join(KNOWN_DIR, filename)
        file.save(filepath)

        encs = get_face_encodings_from_image_file(filepath)
        if not encs:
            flash("No face detected in image", "danger")
            os.remove(filepath)
            return redirect(url_for("register"))

        user = User.query.filter_by(student_id=student_id).first()

        if user:
            # update existing
            prev = json.loads(user.encodings_json) if user.encodings_json else []
            prev.extend(encs)
            user.encodings_json = json.dumps(prev)
            user.name = name
            user.image_filename = filename
        else:
            user = User(
                student_id=student_id,
                name=name,
                image_filename=filename,
                encodings_json=json.dumps(encs)
            )
            db.session.add(user)

        db.session.commit()
        flash("Student registered successfully", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template('register.html')


# ---------- BULK REGISTER (CAMERA) ----------
@app.route('/register_bulk')
@login_required
def register_bulk_page():
    return render_template('register_bulk.html')


@app.route('/register_bulk/submit', methods=['POST'])
@login_required
def register_bulk_submit():
    data = request.get_json()

    student_id = data.get("student_id")
    name = data.get("name")
    images = data.get("images", [])

    if not student_id or not name or not images:
        return jsonify({"success": False, "message": "Missing fields"})

    all_encs = []
    thumbnail_name = None

    for idx, data_url in enumerate(images):
        header, encoded = data_url.split(",", 1)
        image_data = base64.b64decode(encoded)
        img = Image.open(io.BytesIO(image_data)).convert("RGB")

        if thumbnail_name is None:
            thumbnail_name = f"{student_id}_bulk.jpg"
            img.save(os.path.join(KNOWN_DIR, thumbnail_name))

        encs = get_face_encodings_from_pil_image(img)
        if encs:
            all_encs.extend(encs)

    if not all_encs:
        return jsonify({"success": False, "message": "No face detected"})

    user = User.query.filter_by(student_id=student_id).first()

    if user:
        prev = json.loads(user.encodings_json) if user.encodings_json else []
        prev.extend(all_encs)
        user.encodings_json = json.dumps(prev)
        user.name = name
        user.image_filename = thumbnail_name
    else:
        user = User(
            student_id=student_id,
            name=name,
            image_filename=thumbnail_name,
            encodings_json=json.dumps(all_encs)
        )
        db.session.add(user)

    db.session.commit()
    return jsonify({"success": True, "message": "Bulk registration complete"})


# ---------- ATTENDANCE ----------
@app.route('/attendance')
@login_required
def attendance():
    return render_template('attendance.html')


@app.route('/attendance/mark', methods=['POST'])
@login_required
def attendance_mark():
    data_url = request.form.get("image")

    if not data_url:
        return jsonify({"success": False, "message": "No image received"})

    header, encoded = data_url.split(",", 1)
    img_data = base64.b64decode(encoded)
    img = Image.open(io.BytesIO(img_data)).convert("RGB")
    arr = np.array(img)

    import face_recognition
    face_locations = face_recognition.face_locations(arr)
    face_encodings = face_recognition.face_encodings(arr, face_locations)

    if not face_encodings:
        return jsonify({"success": False, "message": "No face detected"})

    known_users = load_all_known_users(db.session, User)

    results = []

    for encoding in face_encodings:
        best_user = None
        best_distance = 999

        for usr, enc_list in known_users:
            dist, matched_idx = compare_face_to_user_encodings(enc_list, encoding, tolerance=0.6)
            if dist is not None and dist < best_distance:
                best_distance = dist
                best_user = usr

        confidence = max(0.0, min(1.0, (0.6 - best_distance) / 0.6)) * 100

        matched = best_distance <= 0.6

        # dedupe
        dedup = False
        if matched:
            today = datetime.utcnow().date()
            existing = Attendance.query.filter(
                Attendance.user_id == best_user.id,
                db.func.date(Attendance.timestamp) == today
            ).first()
            if existing:
                dedup = True
            else:
                new_att = Attendance(
                    user_id=best_user.id,
                    student_id=best_user.student_id,
                    name=best_user.name,
                    timestamp=datetime.utcnow(),
                    status="present"
                )
                db.session.add(new_att)
                db.session.commit()

        results.append({
            "matched": matched,
            "student_id": best_user.student_id if matched else None,
            "name": best_user.name if matched else "Unknown",
            "confidence_pct": round(confidence, 1),
            "deduped": dedup,
            "thumbnail": url_for("known_face_image", user_id=best_user.id) if matched else None
        })

    return jsonify({"success": True, "matches": results})


# ---------- SERVE FACE IMAGES ----------
@app.route('/known_face_image/<int:user_id>')
@login_required
def known_face_image(user_id):
    user = User.query.get(user_id)
    if not user or not user.image_filename:
        return "", 404

    path = os.path.join(KNOWN_DIR, user.image_filename)
    if not os.path.exists(path):
        return "", 404

    return send_file(path, mimetype="image/jpeg")


# ---------- VIEW ATTENDANCE ----------
@app.route('/view_attendance')
@login_required
def view_attendance():
    records = Attendance.query.order_by(Attendance.timestamp.desc()).all()
    return render_template('view_attendance.html', records=records)


# ---------- EXPORT CSV ----------
@app.route('/export/csv')
@login_required
def export_csv():
    records = Attendance.query.all()

    si = io.StringIO()
    writer = csv.writer(si)

    writer.writerow(["Student ID", "Name", "Timestamp", "Status"])
    for r in records:
        writer.writerow([r.student_id, r.name, r.timestamp, r.status])

    response = make_response(si.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=attendance.csv"
    response.headers["Content-type"] = "text/csv"
    return response


# ---------- EXPORT PDF ----------
@app.route('/export/pdf')
@login_required
def export_pdf():
    records = Attendance.query.all()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    elements = []

    styles = getSampleStyleSheet()

    elements.append(Paragraph("Attendance Report", styles["Title"]))
    elements.append(Spacer(1, 20))

    data = [["#", "Student ID", "Name", "Timestamp", "Status"]]
    for i, r in enumerate(records, start=1):
        data.append([i, r.student_id, r.name, str(r.timestamp), r.status])

    tbl = Table(data)
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0d6efd")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))

    elements.append(tbl)

    doc.build(elements)
    buffer.seek(0)

    return send_file(buffer, download_name="attendance.pdf", as_attachment=True)



if __name__ == "__main__":
    app.run(debug=True)
