import os
import re
from datetime import date, datetime
from pathlib import Path
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
import db
from demo_seed import ensure_demo_data


BASE_DIR = Path(__file__).resolve().parent
SQL_DIR = BASE_DIR / "sql"

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "local-secret-key")
ADMIN_LOGIN = "admin"
ADMIN_PASSWORD = "admin"


ENCOUNTER_TYPE_CHOICES = [
    ("outpatient", "Амбулаторный прием"),
    ("inpatient", "Госпитализация"),
    ("consultation", "Консультация"),
    ("follow_up", "Повторный прием"),
    ("diagnostic", "Диагностика"),
    ("day_hospital", "Дневной стационар"),
]
ENCOUNTER_TYPE_LABELS = {code: label for code, label in ENCOUNTER_TYPE_CHOICES}
FREQUENCY_LABELS = {
    "one_time": "Однократно",
    "once_daily": "1 раз в день",
    "twice_daily": "2 раза в день",
    "three_times_daily": "3 раза в день",
    "weekly": "1 раз в неделю",
}
ASSIGNMENT_TYPE_LABELS = {
    "procedure": "Процедура",
    "medication": "Медикамент",
}
DIAGNOSIS_TYPE_CHOICES = [
    ("primary", "Основной"),
    ("secondary", "Сопутствующий"),
    ("followup", "Повторный"),
]
DIAGNOSIS_TYPE_LABELS = {code: label for code, label in DIAGNOSIS_TYPE_CHOICES}
STAFF_TYPE_CHOICES = [
    ("doctor", "Врач"),
    ("nurse", "Медсестра"),
    ("accountant", "Бухгалтер"),
    ("administrator", "Администратор"),
    ("lab_assistant", "Лаборант"),
    ("paramedic", "Фельдшер"),
]
STAFF_TYPE_LABELS = {code: label for code, label in STAFF_TYPE_CHOICES}
INSTITUTION_TYPE_CHOICES = [
    ("Hospital", "Больница"),
    ("Center", "Центр"),
    ("Polyclinic", "Поликлиника"),
    ("Clinic", "Клиника"),
]
INSTITUTION_TYPE_LABELS = {code: label for code, label in INSTITUTION_TYPE_CHOICES}
DEPARTMENT_TYPE_CHOICES = [
    ("Inpatient", "Стационар"),
    ("Outpatient", "Амбулаторное"),
    ("Diagnostic", "Диагностическое"),
    ("DayCare", "Дневной стационар"),
    ("Emergency", "Экстренное"),
]
DEPARTMENT_TYPE_LABELS = {code: label for code, label in DEPARTMENT_TYPE_CHOICES}


def load_selects(path):
    text = Path(path).read_text(encoding="utf-8")
    parts = [p.strip() for p in text.split(";") if p.strip()]
    queries = {}
    i = 0
    while i < len(parts):
        m = re.fullmatch(r"SELECT\s+'([A-Z0-9_]+)'", parts[i], flags=re.IGNORECASE)
        if m and i + 1 < len(parts):
            queries[m.group(1)] = parts[i + 1]
            i += 2
        else:
            i += 1
    return queries


SELECTS = {}


def format_ui_date(value):
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%d.%m.%Y")
    if isinstance(value, date):
        return value.strftime("%d.%m.%Y")
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return ""
        normalized = text.replace("T", " ")
        try:
            if len(normalized) >= 19:
                return datetime.fromisoformat(normalized[:19]).strftime("%d.%m.%Y")
            return date.fromisoformat(normalized[:10]).strftime("%d.%m.%Y")
        except ValueError:
            return text
    return str(value)


app.jinja_env.filters["ui_date"] = format_ui_date


def init_db():
    db.execute_script_file(SQL_DIR / "00_create.sql")
    db.execute_script_file(SQL_DIR / "03_procedures.sql")
    db.execute_script_file(SQL_DIR / "04_triggers.sql")
    db.execute("ALTER TABLE doctors ADD COLUMN IF NOT EXISTS license_number varchar")
    seed_check = db.query("SELECT COUNT(*) AS cnt FROM medical_institutions")
    if seed_check and int(seed_check[0]["cnt"]) == 0:
        db.execute_script_file(SQL_DIR / "01_seed.sql")
    ensure_demo_data()


def require_doctor():
    return session.get("role") == "doctor" and bool(session.get("doctor_id"))


def require_patient():
    return session.get("role") == "patient" and bool(session.get("patient_id"))


def require_admin():
    return session.get("role") == "admin" and bool(session.get("admin_login"))


def parse_dt(value):
    if not value:
        return None
    return datetime.fromisoformat(value)


def parse_int(value):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def next_id(select_name):
    rows = db.query(SELECTS[select_name])
    return int(rows[0]["id"])


def next_table_id(table_name):
    rows = db.query(f"SELECT COALESCE(MAX(id), 0) + 1 AS id FROM {table_name}")
    return int(rows[0]["id"])


def parse_bool(value):
    return str(value).strip().lower() in {"1", "true", "on", "yes", "y"}


def doctor_nav():
    return [
        (url_for("doctor_my_patients"), "Мои пациенты"),
        (url_for("doctor_create_encounter"), "Новый прием"),
        (url_for("logout"), "Выход"),
    ]


def patient_nav():
    return [
        (url_for("patient_encounters"), "Мои приемы"),
        (url_for("patient_diagnoses"), "Мои диагнозы"),
        (url_for("patient_treatments"), "Мои назначения"),
        (url_for("logout"), "Выход"),
    ]


def admin_nav():
    return [
        (url_for("admin_dashboard"), "Админ"),
        (url_for("admin_staff_list"), "Сотрудники"),
        (url_for("admin_institutions_list"), "Учреждения"),
        (url_for("admin_departments_list"), "Отделения"),
        (url_for("admin_patients_list"), "Пациенты"),
        (url_for("admin_medications_list"), "Препараты"),
        (url_for("admin_procedures_list"), "Процедуры"),
        (url_for("admin_specializations_list"), "Специализации"),
        (url_for("logout"), "Выход"),
    ]


def render_doctor(template_name, **context):
    return render_template(template_name, nav_links=doctor_nav(), **context)


def render_patient(template_name, **context):
    return render_template(template_name, nav_links=patient_nav(), **context)


def render_admin(template_name, **context):
    return render_template(template_name, nav_links=admin_nav(), **context)


def get_patient(patient_id):
    rows = db.query(SELECTS["PATIENT_BY_ID"], [patient_id])
    return rows[0] if rows else None


def get_all_patients():
    return db.query(SELECTS["PATIENTS_LIST"])


def get_beds():
    return db.query(SELECTS["BEDS_LIST"])


def get_free_beds():
    return db.query(SELECTS["BEDS_FREE_LIST"])


def get_procedures():
    return db.query(SELECTS["PROCEDURES_LIST"])


def get_medications():
    return db.query(SELECTS["MEDICATIONS_LIST"])


def get_doctor_encounter(encounter_id):
    rows = db.query(SELECTS["DOCTOR_ENCOUNTER_BY_ID"], [encounter_id, session["doctor_id"]])
    return rows[0] if rows else None


def get_doctor_patient_or_404(patient_id):
    can_view = db.query(SELECTS["DOCTOR_CAN_VIEW_PATIENT"], [session["doctor_id"], patient_id])
    if not can_view:
        abort(403)
    patient = get_patient(patient_id)
    if not patient:
        abort(404)
    return patient


def get_doctor_encounter_or_404(encounter_id):
    encounter = get_doctor_encounter(encounter_id)
    if not encounter:
        abort(404)
    return encounter


def build_encounter_form_data(form, default_patient_id=None):
    return {
        "patient_id": form.get("patient_id", str(default_patient_id or "")).strip(),
        "bed_id": form.get("bed_id", "").strip(),
        "type": form.get("type", "").strip(),
        "start_datetime": form.get("start_datetime", "").strip(),
        "end_datetime": form.get("end_datetime", "").strip(),
    }


def build_diagnosis_form_data(form):
    diagnosed_at = form.get("diagnosed_at", "").strip()
    return {
        "icd10_code": form.get("icd10_code", "").strip(),
        "diagnosis_type": form.get("diagnosis_type", "").strip(),
        "diagnosed_at": diagnosed_at,
        "notes": form.get("notes", "").strip(),
    }


def build_treatment_form_data(form):
    return {
        "assignment_kind": form.get("assignment_kind", "procedure").strip() or "procedure",
        "procedure_id": form.get("procedure_id", "").strip(),
        "medication_id": form.get("medication_id", "").strip(),
        "start_date": form.get("start_date", "").strip(),
        "end_date": form.get("end_date", "").strip(),
        "frequency": form.get("frequency", "").strip(),
        "type": form.get("type", "").strip(),
        "note": form.get("note", "").strip(),
    }


def normalize_passport_input(passport_text):
    digits = re.sub(r"\s+", "", passport_text or "")
    if not re.fullmatch(r"\d{10}", digits):
        return None, None
    return f"{digits[:4]} {digits[4:]}", digits


def validate_patient_search(search_field, search_query, date_from, date_to):
    allowed_fields = {"name", "phone", "snus", "passport", "email", "sex", "birth_date"}
    if search_field not in allowed_fields:
        return "name", search_query, "Некорректное поле поиска"
    query = search_query.strip()
    if search_field == "sex":
        if query in {"М", "M"}:
            return search_field, "M", ""
        if query in {"Ж", "F"}:
            return search_field, "F", ""
        if query == "":
            return search_field, "", ""
        return search_field, query, "Пол: выберите М или Ж"
    if search_field == "birth_date":
        if not date_from and not date_to:
            return search_field, query, "Укажите хотя бы одну дату интервала"
        if date_from and date_to and date_from > date_to:
            return search_field, query, "Дата начала интервала позже даты окончания"
        return search_field, query, ""
    if query == "":
        return search_field, query, ""
    patterns = {
        "name": r"^[A-Za-zА-Яа-яЁё\s\-]{2,80}$",
        "phone": r"^\+?[0-9\-\s\(\)]{6,22}$",
        "snus": r"^[0-9\-\s]{8,20}$",
        "passport": r"^\d{4}\s?\d{6}$",
        "email": r"^[^\s@]+@[^\s@]+\.[^\s@]+$",
    }
    messages = {
        "name": "Имя: минимум 2 символа, только буквы, пробел или дефис",
        "phone": "Телефон: допустимы цифры, пробелы, +, (), дефис",
        "snus": "СНИЛС: только цифры, пробелы и дефис",
        "passport": "Паспорт: 10 цифр, формат 4515 100155 или 4515100155",
        "email": "Email в формате name@example.com",
    }
    if not re.fullmatch(patterns[search_field], query):
        return search_field, query, messages[search_field]
    return search_field, query, ""


def validate_patient_encounters_search(search_field, search_query, date_from, date_to):
    allowed_fields = {"doctor", "type", "date_start"}
    if search_field not in allowed_fields:
        return "doctor", "Некорректное поле поиска"
    if search_field == "doctor":
        if search_query and not re.fullmatch(r"^[A-Za-zА-Яа-яЁё\s\-]{2,120}$", search_query):
            return search_field, "ФИО врача: только буквы, пробелы и дефис"
    elif search_field == "type":
        if search_query and search_query not in ENCOUNTER_TYPE_LABELS:
            return search_field, "Выберите корректный тип приема"
    elif search_field == "date_start":
        if not date_from and not date_to:
            return search_field, "Укажите хотя бы одну дату интервала"
        if date_from and date_to and date_from > date_to:
            return search_field, "Дата начала интервала позже даты окончания"
    return search_field, ""


def validate_admin_search(search_field, search_query, default_field, allowed_fields, patterns, messages):
    field = (search_field or "").strip().lower()
    query = (search_query or "").strip()
    if not field:
        return "", query, ""
    if field not in allowed_fields:
        return default_field, query, "Некорректное поле поиска"
    if query == "":
        return field, query, ""
    pattern = patterns.get(field)
    if pattern and not re.fullmatch(pattern, query):
        return field, query, messages.get(field, "Некорректное значение поиска")
    return field, query, ""


def validate_encounter_form(form_data, current_encounter=None):
    patient_id = parse_int(form_data["patient_id"])
    bed_id = parse_int(form_data["bed_id"])
    try:
        start_dt = parse_dt(form_data["start_datetime"])
        end_dt = parse_dt(form_data["end_datetime"])
    except ValueError:
        start_dt = None
        end_dt = None
    if not patient_id:
        return "Пациент не найден", None
    patient = get_patient(patient_id)
    if not patient:
        return "Пациент не найден", None
    if current_encounter and current_encounter["patient_id"] != patient_id:
        return "Нельзя менять пациента у существующего приема", None
    if form_data["type"] not in ENCOUNTER_TYPE_LABELS:
        return "Выберите тип приема из списка", None
    if form_data["type"] == "inpatient":
        if form_data["bed_id"] and not bed_id:
            return "Выберите корректную койку", None
        if not bed_id:
            return "Для госпитализации нужно выбрать свободную койку", None
        if not db.query(SELECTS["BED_IS_FREE"], [bed_id]):
            return "Койка занята или недоступна", None
    else:
        bed_id = None
    if not start_dt or not end_dt:
        return "Проверьте даты приема", None
    if start_dt > end_dt:
        return "Дата начала должна быть раньше даты окончания", None
    return "", {
        "patient": patient,
        "patient_id": patient_id,
        "bed_id": bed_id,
        "type": form_data["type"],
        "start_datetime": start_dt,
        "end_datetime": end_dt,
    }


def validate_diagnosis_form(form_data):
    try:
        diagnosed_at = parse_dt(form_data["diagnosed_at"])
    except ValueError:
        diagnosed_at = None
    if not form_data["icd10_code"]:
        return "Укажите код МКБ-10", None
    if not form_data["diagnosis_type"]:
        return "Укажите тип диагноза", None
    if form_data["diagnosis_type"] not in DIAGNOSIS_TYPE_LABELS:
        return "Выберите тип диагноза из списка", None
    if not diagnosed_at:
        return "Укажите корректные дату и время постановки диагноза", None
    if not form_data["notes"]:
        return "Укажите описание диагноза", None
    return "", {
        "icd10_code": form_data["icd10_code"],
        "diagnosis_type": form_data["diagnosis_type"],
        "diagnosed_at": diagnosed_at,
        "notes": form_data["notes"],
    }


def validate_treatment_form(form_data):
    procedure_id = parse_int(form_data["procedure_id"])
    medication_id = parse_int(form_data["medication_id"])
    is_procedure = form_data["assignment_kind"] == "procedure"
    selected_count = int(bool(procedure_id)) + int(bool(medication_id))
    if selected_count != 1:
        return "Нужно выбрать ровно один вариант: процедуру или лекарство", None
    if is_procedure and not procedure_id:
        return "Выберите процедуру", None
    if not is_procedure and not medication_id:
        return "Выберите лекарство", None
    if procedure_id and not db.query(SELECTS["PROCEDURE_EXISTS"], [procedure_id]):
        return "Процедура не найдена", None
    if medication_id and not db.query(SELECTS["MEDICATION_EXISTS"], [medication_id]):
        return "Лекарство не найдено", None
    if not form_data["start_date"] or not form_data["end_date"]:
        return "Укажите даты назначения", None
    if form_data["start_date"] > form_data["end_date"]:
        return "Дата начала должна быть раньше даты окончания", None
    if not form_data["frequency"]:
        return "Укажите частоту", None
    if not form_data["type"]:
        return "Укажите тип назначения", None
    if not form_data["note"]:
        return "Укажите примечание", None
    return "", {
        "procedure_id": procedure_id if is_procedure else None,
        "medication_id": medication_id if not is_procedure else None,
        "start_date": form_data["start_date"],
        "end_date": form_data["end_date"],
        "frequency": form_data["frequency"],
        "type": form_data["type"],
        "note": form_data["note"],
    }


@app.route("/")
def index():
    role = session.get("role")
    if role == "admin":
        return redirect(url_for("admin_dashboard"))
    if role == "doctor":
        return redirect(url_for("doctor_my_patients"))
    if role == "patient":
        return redirect(url_for("patient_encounters"))
    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    selected_role = request.form.get("role", "doctor").strip().lower() if request.method == "POST" else "doctor"
    if request.method == "POST":
        role = selected_role
        user_id_raw = request.form.get("user_id", "").strip()
        admin_login = request.form.get("admin_login", "").strip()
        admin_password = request.form.get("admin_password", "")
        if role not in {"doctor", "patient", "admin"}:
            error = "Выберите роль"
        elif role == "admin":
            if admin_login == ADMIN_LOGIN and admin_password == ADMIN_PASSWORD:
                session.clear()
                session["role"] = "admin"
                session["admin_login"] = admin_login
                return redirect(url_for("admin_dashboard"))
            error = "Неверный логин или пароль администратора"
        else:
            user_id = parse_int(user_id_raw)
            if user_id is None:
                error = "ID должен быть числом"
            elif role == "doctor":
                exists = db.query(SELECTS["AUTH_DOCTOR_EXISTS"], [user_id])
                if exists:
                    session.clear()
                    session["role"] = "doctor"
                    session["doctor_id"] = user_id
                    return redirect(url_for("doctor_my_patients"))
                error = "Врач не найден"
            elif role == "patient":
                exists = db.query(SELECTS["AUTH_PATIENT_EXISTS"], [user_id])
                if exists:
                    session.clear()
                    session["role"] = "patient"
                    session["patient_id"] = user_id
                    return redirect(url_for("patient_encounters"))
                error = "Пациент не найден"
    return render_template(
        "login.html",
        error=error,
        nav_links=[],
        brand_link=False,
        selected_role=selected_role,
    )


@app.route("/doctor/my_patients")
def doctor_my_patients():
    if not require_doctor():
        abort(403)
    search_field = request.args.get("search_field", "name").strip().lower()
    search_query = request.args.get("search_query", "").strip()
    if search_field in {"name", "phone", "snus", "passport", "email"} and not search_query:
        search_query = request.args.get("search_query_text", "").strip()
    if search_field == "sex" and not search_query:
        search_query = request.args.get("search_query_sex", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    search_field, search_query, search_error = validate_patient_search(search_field, search_query, date_from, date_to)
    passport_digits = ""
    if search_field == "passport" and search_query and not search_error:
        normalized_passport, passport_digits = normalize_passport_input(search_query)
        search_query = normalized_passport or search_query
    if search_error:
        rows = []
    else:
        wildcard = f"%{passport_digits}%" if search_field == "passport" else f"%{search_query}%"
        rows = db.query(
            SELECTS["DOCTOR_PATIENTS_SEARCH_BY_FIELD"],
            [
                session["doctor_id"],
                search_field, search_query, wildcard,
                search_field, search_query, wildcard,
                search_field, search_query, wildcard,
                search_field, search_query, wildcard,
                search_field, search_query, wildcard,
                search_field, search_query, search_query,
                search_field, date_from or None, date_from or None, date_to or None, date_to or None,
            ],
        )
    return render_doctor(
        "doctor_my_patients.html",
        title="Мои пациенты",
        patients=rows,
        search_field=search_field,
        search_query=search_query,
        search_error=search_error,
        date_from=date_from,
        date_to=date_to,
    )


@app.route("/doctor/patient/<int:patient_id>")
def doctor_patient(patient_id):
    if not require_doctor():
        abort(403)
    patient = get_doctor_patient_or_404(patient_id)
    encounters = db.query(SELECTS["DOCTOR_PATIENT_ENCOUNTERS"], [session["doctor_id"], patient_id])
    diagnoses = db.query(SELECTS["DOCTOR_PATIENT_DIAGNOSES"], [session["doctor_id"], patient_id])
    for row in diagnoses:
        row["diagnosis_type_ru"] = DIAGNOSIS_TYPE_LABELS.get(row["diagnosis_type"], row["diagnosis_type"])
    treatments = db.query(SELECTS["DOCTOR_PATIENT_TREATMENTS"], [session["doctor_id"], patient_id])
    return render_doctor(
        "doctor_patient.html",
        title=f"Пациент {patient['name']}",
        patient=patient,
        encounters=encounters,
        diagnoses=diagnoses,
        treatments=treatments,
    )


@app.route("/doctor/create_encounter", methods=["GET", "POST"])
def doctor_create_encounter():
    if not require_doctor():
        abort(403)
    patient_id_raw = request.args.get("patient_id", "").strip()
    patient_id = parse_int(patient_id_raw)
    patient = get_patient(patient_id) if patient_id else None
    form_data = build_encounter_form_data(request.form if request.method == "POST" else request.args, patient_id)
    error = ""
    patients = get_all_patients()
    if request.method == "POST":
        error, cleaned = validate_encounter_form(form_data)
        if not error:
            new_id = next_id("NEXT_ENCOUNTER_ID")
            db.execute(
                "INSERT INTO encounters(id, patient_id, doctor_id, bed_id, type, start_datetime, end_datetime) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                [
                    new_id,
                    cleaned["patient_id"],
                    session["doctor_id"],
                    cleaned["bed_id"],
                    cleaned["type"],
                    cleaned["start_datetime"],
                    cleaned["end_datetime"],
                ],
            )
            flash(f"Прием #{new_id} создан. Добавьте диагнозы и назначения.")
            return redirect(url_for("doctor_compose_encounter", encounter_id=new_id))
    return render_doctor(
        "doctor_create_encounter.html",
        title="Новый прием",
        error=error,
        form_data=form_data,
        patient=patient,
        patients=patients,
        beds=get_free_beds(),
        encounter_type_choices=ENCOUNTER_TYPE_CHOICES,
    )


@app.route("/doctor/encounter/<int:encounter_id>/compose", methods=["GET", "POST"])
def doctor_compose_encounter(encounter_id):
    if not require_doctor():
        abort(403)
    encounter = get_doctor_encounter_or_404(encounter_id)
    patient = get_doctor_patient_or_404(encounter["patient_id"])
    diagnosis_error = ""
    treatment_error = ""
    diagnosis_form = {
        "icd10_code": "",
        "diagnosis_type": "",
        "diagnosed_at": encounter["start_datetime"].strftime("%Y-%m-%dT%H:%M"),
        "notes": "",
    }
    treatment_form = {
        "assignment_kind": "procedure",
        "procedure_id": "",
        "medication_id": "",
        "start_date": encounter["start_datetime"].date().isoformat(),
        "end_date": encounter["end_datetime"].date().isoformat(),
        "frequency": "",
        "type": "",
        "note": "",
    }
    if request.method == "POST":
        action = request.form.get("action", "").strip()
        if action == "finish":
            return redirect(url_for("doctor_patient", patient_id=patient["id"]))
        if action == "add_diagnosis":
            diagnosis_form = build_diagnosis_form_data(request.form)
            diagnosis_error, cleaned = validate_diagnosis_form(diagnosis_form)
            if not diagnosis_error:
                new_id = next_id("NEXT_DIAGNOSIS_ID")
                db.execute(
                    "INSERT INTO diagnoses(id, patient_id, encounter_id, icd10_code, diagnosis_type, diagnosed_at, notes) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    [
                        new_id,
                        patient["id"],
                        encounter_id,
                        cleaned["icd10_code"],
                        cleaned["diagnosis_type"],
                        cleaned["diagnosed_at"],
                        cleaned["notes"],
                    ],
                )
                flash(f"Диагноз #{new_id} добавлен")
                return redirect(url_for("doctor_compose_encounter", encounter_id=encounter_id))
        elif action == "add_treatment":
            treatment_form = build_treatment_form_data(request.form)
            treatment_error, cleaned = validate_treatment_form(treatment_form)
            if not treatment_error:
                new_id = next_id("NEXT_TREATMENT_ID")
                db.execute(
                    "INSERT INTO treatment_items(id, encounter_id, procedure_id, medication_id, start_date, end_date, frequency, type, note) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    [
                        new_id,
                        encounter_id,
                        cleaned["procedure_id"],
                        cleaned["medication_id"],
                        cleaned["start_date"],
                        cleaned["end_date"],
                        cleaned["frequency"],
                        cleaned["type"],
                        cleaned["note"],
                    ],
                )
                flash(f"Назначение #{new_id} добавлено")
                return redirect(url_for("doctor_compose_encounter", encounter_id=encounter_id))
        else:
            diagnosis_error = "Некорректное действие формы"
    diagnoses = db.query(SELECTS["DOCTOR_ENCOUNTER_DIAGNOSES"], [encounter_id, session["doctor_id"]])
    treatments = db.query(SELECTS["DOCTOR_ENCOUNTER_TREATMENTS"], [encounter_id, session["doctor_id"]])
    for row in diagnoses:
        row["diagnosis_type_ru"] = DIAGNOSIS_TYPE_LABELS.get(row["diagnosis_type"], row["diagnosis_type"])
    for row in treatments:
        row["frequency_ru"] = FREQUENCY_LABELS.get(row["frequency"], row["frequency"])
        row["assignment_type_ru"] = ASSIGNMENT_TYPE_LABELS.get(row["type"], row["type"])
    return render_doctor(
        "doctor_compose_encounter.html",
        title=f"Наполнение приема #{encounter_id}",
        encounter=encounter,
        patient=patient,
        diagnosis_error=diagnosis_error,
        treatment_error=treatment_error,
        diagnosis_form=diagnosis_form,
        treatment_form=treatment_form,
        diagnoses=diagnoses,
        treatments=treatments,
        diagnosis_type_choices=DIAGNOSIS_TYPE_CHOICES,
        procedures=get_procedures(),
        medications=get_medications(),
    )


@app.route("/doctor/edit_encounter/<int:encounter_id>", methods=["GET", "POST"])
def doctor_edit_encounter(encounter_id):
    if not require_doctor():
        abort(403)
    encounter = get_doctor_encounter_or_404(encounter_id)
    patient = get_doctor_patient_or_404(encounter["patient_id"])
    if request.method == "POST":
        form_data = build_encounter_form_data(request.form, encounter["patient_id"])
        error, cleaned = validate_encounter_form(form_data, encounter)
        if not error:
            db.execute(
                "UPDATE encounters SET bed_id=%s, type=%s, start_datetime=%s, end_datetime=%s WHERE id=%s AND doctor_id=%s",
                [
                    cleaned["bed_id"],
                    cleaned["type"],
                    cleaned["start_datetime"],
                    cleaned["end_datetime"],
                    encounter_id,
                    session["doctor_id"],
                ],
            )
            flash(f"Прием #{encounter_id} обновлен")
            return redirect(url_for("doctor_patient", patient_id=encounter["patient_id"]))
    else:
        error = ""
        form_data = {
            "patient_id": str(encounter["patient_id"]),
            "bed_id": "" if encounter["bed_id"] is None else str(encounter["bed_id"]),
            "type": encounter["type"],
            "start_datetime": encounter["start_datetime"].strftime("%Y-%m-%dT%H:%M"),
            "end_datetime": encounter["end_datetime"].strftime("%Y-%m-%dT%H:%M"),
        }
    return render_doctor(
        "doctor_edit_encounter.html",
        title=f"Прием {encounter_id}",
        encounter=encounter,
        patient=patient,
        error=error,
        form_data=form_data,
        beds=get_beds(),
        encounter_type_choices=ENCOUNTER_TYPE_CHOICES,
    )


@app.route("/doctor/add_diagnosis/<int:encounter_id>", methods=["GET", "POST"])
def doctor_add_diagnosis(encounter_id):
    if not require_doctor():
        abort(403)
    encounter = get_doctor_encounter_or_404(encounter_id)
    patient = get_doctor_patient_or_404(encounter["patient_id"])
    if request.method == "POST":
        form_data = build_diagnosis_form_data(request.form)
        error, cleaned = validate_diagnosis_form(form_data)
        if not error:
            new_id = next_id("NEXT_DIAGNOSIS_ID")
            db.execute(
                "INSERT INTO diagnoses(id, patient_id, encounter_id, icd10_code, diagnosis_type, diagnosed_at, notes) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                [
                    new_id,
                    patient["id"],
                    encounter_id,
                    cleaned["icd10_code"],
                    cleaned["diagnosis_type"],
                    cleaned["diagnosed_at"],
                    cleaned["notes"],
                ],
            )
            flash(f"Диагноз #{new_id} добавлен")
            return redirect(url_for("doctor_patient", patient_id=patient["id"]))
    else:
        error = ""
        form_data = {
            "icd10_code": "",
            "diagnosis_type": "",
            "diagnosed_at": encounter["start_datetime"].strftime("%Y-%m-%dT%H:%M"),
            "notes": "",
        }
    return render_doctor(
        "doctor_add_diagnosis.html",
        title="Новый диагноз",
        encounter=encounter,
        patient=patient,
        error=error,
        form_data=form_data,
        diagnosis_type_choices=DIAGNOSIS_TYPE_CHOICES,
    )


@app.route("/doctor/add_treatment/<int:encounter_id>", methods=["GET", "POST"])
def doctor_add_treatment(encounter_id):
    if not require_doctor():
        abort(403)
    encounter = get_doctor_encounter_or_404(encounter_id)
    patient = get_doctor_patient_or_404(encounter["patient_id"])
    if request.method == "POST":
        form_data = build_treatment_form_data(request.form)
        error, cleaned = validate_treatment_form(form_data)
        if not error:
            new_id = next_id("NEXT_TREATMENT_ID")
            db.execute(
                "INSERT INTO treatment_items(id, encounter_id, procedure_id, medication_id, start_date, end_date, frequency, type, note) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                [
                    new_id,
                    encounter_id,
                    cleaned["procedure_id"],
                    cleaned["medication_id"],
                    cleaned["start_date"],
                    cleaned["end_date"],
                    cleaned["frequency"],
                    cleaned["type"],
                    cleaned["note"],
                ],
            )
            flash(f"Назначение #{new_id} добавлено")
            return redirect(url_for("doctor_patient", patient_id=patient["id"]))
    else:
        error = ""
        form_data = {
            "assignment_kind": "procedure",
            "procedure_id": "",
            "medication_id": "",
            "start_date": encounter["start_datetime"].date().isoformat(),
            "end_date": encounter["end_datetime"].date().isoformat(),
            "frequency": "",
            "type": "",
            "note": "",
        }
    return render_doctor(
        "doctor_add_treatment.html",
        title="Новое назначение",
        encounter=encounter,
        patient=patient,
        error=error,
        form_data=form_data,
        procedures=get_procedures(),
        medications=get_medications(),
    )


@app.route("/patient/encounters")
def patient_encounters():
    if not require_patient():
        abort(403)
    search_field = request.args.get("search_field", "doctor").strip()
    focus_encounter_id = parse_int(request.args.get("focus_encounter", "").strip())
    search_query = request.args.get("search_query", "").strip()
    if search_field == "doctor" and not search_query:
        search_query = request.args.get("search_query_text", "").strip()
    if search_field == "type" and not search_query:
        search_query = request.args.get("search_query_type", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    search_field, search_error = validate_patient_encounters_search(search_field, search_query, date_from, date_to)
    if search_error:
        rows = []
    else:
        doctor_wildcard = f"%{search_query}%"
        rows = db.query(
            SELECTS["PATIENT_ENCOUNTERS_SEARCH"],
            [
                session["patient_id"],
                search_field,
                search_query,
                doctor_wildcard,
                search_field,
                search_query,
                search_query,
                search_field,
                date_from or None,
                date_from or None,
                date_to or None,
                date_to or None,
            ],
        )
    for row in rows:
        row["type_ru"] = ENCOUNTER_TYPE_LABELS.get(row["type"], row["type"])
        row["is_focused"] = bool(focus_encounter_id) and row["id"] == focus_encounter_id
    details_by_encounter = {row["id"]: {"diagnoses": [], "treatments": []} for row in rows}
    if details_by_encounter:
        diagnosis_rows = db.query(SELECTS["PATIENT_ENCOUNTER_DETAILS_DIAGNOSES"], [session["patient_id"]])
        treatment_rows = db.query(SELECTS["PATIENT_ENCOUNTER_DETAILS_TREATMENTS"], [session["patient_id"]])
        for row in diagnosis_rows:
            bucket = details_by_encounter.get(row["encounter_id"])
            if bucket is None:
                continue
            diagnosis_type_ru = DIAGNOSIS_TYPE_LABELS.get(row["diagnosis_type"], row["diagnosis_type"])
            diagnosis_title = f"{row['icd10_code']} ({diagnosis_type_ru})"
            bucket["diagnoses"].append({"id": row["id"], "title": diagnosis_title})
        for row in treatment_rows:
            bucket = details_by_encounter.get(row["encounter_id"])
            if bucket is None:
                continue
            treatment_title = row["procedure_name"] or row["medication_name"] or "Назначение"
            bucket["treatments"].append({"id": row["id"], "title": treatment_title})
    return render_patient(
        "patient_encounters.html",
        title="Мои приемы",
        encounters=rows,
        details_by_encounter=details_by_encounter,
        search_field=search_field,
        search_query=search_query,
        search_error=search_error,
        date_from=date_from,
        date_to=date_to,
        focus_encounter_id=focus_encounter_id,
        encounter_type_choices=ENCOUNTER_TYPE_CHOICES,
    )


@app.route("/patient/diagnoses")
def patient_diagnoses():
    if not require_patient():
        abort(403)
    focus_id = parse_int(request.args.get("focus", "").strip())
    rows = db.query(SELECTS["PATIENT_DIAGNOSES"], [session["patient_id"]])
    for row in rows:
        row["encounter_type_ru"] = ENCOUNTER_TYPE_LABELS.get(row["encounter_type"], row["encounter_type"])
        row["diagnosis_type_ru"] = DIAGNOSIS_TYPE_LABELS.get(row["diagnosis_type"], row["diagnosis_type"])
        row["is_focused"] = bool(focus_id) and row["id"] == focus_id
    return render_patient(
        "patient_diagnoses.html",
        title="Мои диагнозы",
        diagnoses=rows,
        focus_id=focus_id,
    )


@app.route("/patient/treatments")
def patient_treatments():
    if not require_patient():
        abort(403)
    focus_id = parse_int(request.args.get("focus", "").strip())
    only_active = request.args.get("only_active", "").strip() == "1"
    rows = db.query(SELECTS["PATIENT_TREATMENTS"], [session["patient_id"]])
    today = date.today()
    normalized_rows = []
    for row in rows:
        row["frequency_ru"] = FREQUENCY_LABELS.get(row["frequency"], row["frequency"])
        row["type_ru"] = ENCOUNTER_TYPE_LABELS.get(row["encounter_type"], row["encounter_type"])
        row["assignment_type_ru"] = ASSIGNMENT_TYPE_LABELS.get(row["type"], row["type"])
        row["is_focused"] = bool(focus_id) and row["id"] == focus_id
        row["is_expired"] = row["end_date"] < today
        if only_active and row["is_expired"]:
            continue
        normalized_rows.append(row)
    return render_patient(
        "patient_treatments.html",
        title="Мои назначения",
        treatments=normalized_rows,
        only_active=only_active,
        focus_id=focus_id,
    )


@app.route("/admin")
def admin_dashboard():
    if not require_admin():
        abort(403)
    stats = {
        "staff": db.query("SELECT COUNT(*) AS cnt FROM staff")[0]["cnt"],
        "institutions": db.query("SELECT COUNT(*) AS cnt FROM medical_institutions")[0]["cnt"],
        "departments": db.query("SELECT COUNT(*) AS cnt FROM departments")[0]["cnt"],
        "patients": db.query("SELECT COUNT(*) AS cnt FROM patients")[0]["cnt"],
        "medications": db.query("SELECT COUNT(*) AS cnt FROM medication")[0]["cnt"],
        "procedures": db.query("SELECT COUNT(*) AS cnt FROM procedures")[0]["cnt"],
        "specializations": db.query("SELECT COUNT(*) AS cnt FROM specializations")[0]["cnt"],
    }
    return render_admin("admin_dashboard.html", title="Админ-панель", stats=stats)


@app.route("/admin/staff")
def admin_staff_list():
    if not require_admin():
        abort(403)
    search_field = request.args.get("search_field", "").strip().lower()
    search_query = request.args.get("search_query", "").strip()
    if not search_query:
        search_query = request.args.get("search_query_text", "").strip()
    allowed_fields = {"id", "name", "email", "department", "institution"}
    patterns = {
        "id": r"^\d{1,10}$",
        "name": r"^[A-Za-zА-Яа-яЁё\s\-]{2,120}$",
        "email": r"^[^\s@]+@[^\s@]+\.[^\s@]+$",
        "department": r"^.{2,120}$",
        "institution": r"^.{2,120}$",
    }
    messages = {
        "id": "ID: только цифры",
        "name": "ФИО: минимум 2 символа, буквы/пробел/дефис",
        "email": "Email в формате name@example.com",
        "department": "Название отделения: минимум 2 символа",
        "institution": "Название учреждения: минимум 2 символа",
    }
    search_field, search_query, search_error = validate_admin_search(
        search_field, search_query, "name", allowed_fields, patterns, messages
    )
    focus_id = parse_int(request.args.get("focus", "").strip())
    if search_error:
        rows = []
    else:
        wildcard = f"%{search_query}%"
        rows = db.query(
            """
            SELECT s.id, s.name, s.staff_type, s.phone, s.email, s.is_active, d.id AS department_id,
                   d.name AS department_name, mi.id AS institution_id, mi.name AS institution_name,
                   dr.experience_years, dr.license_number,
                   (
                     SELECT sp.name
                     FROM doctors_specializations ds
                     JOIN specializations sp ON sp.id = ds.specialization_id
                     WHERE ds.doctor_id = s.id
                     ORDER BY ds.specialization_id
                     LIMIT 1
                   ) AS specialization_name
            FROM staff s
            JOIN departments d ON d.id = s.department_id
            JOIN medical_institutions mi ON mi.id = d.institution_id
            LEFT JOIN doctors dr ON dr.id = s.id
            WHERE (
              %s = ''
              OR (%s = 'id' AND CAST(s.id AS TEXT) = %s)
              OR (%s = 'name' AND LOWER(s.name) LIKE LOWER(%s))
              OR (%s = 'email' AND LOWER(s.email) LIKE LOWER(%s))
              OR (%s = 'department' AND LOWER(d.name) LIKE LOWER(%s))
              OR (%s = 'institution' AND LOWER(mi.name) LIKE LOWER(%s))
            )
            ORDER BY s.name, s.id
            """,
            [
                search_query,
                search_field, search_query,
                search_field, wildcard,
                search_field, wildcard,
                search_field, wildcard,
                search_field, wildcard,
            ],
        )
    for row in rows:
        row["staff_type_ru"] = STAFF_TYPE_LABELS.get(row["staff_type"], row["staff_type"])
        row["is_focused"] = bool(focus_id) and row["id"] == focus_id
    return render_admin(
        "admin_staff_list.html",
        title="Сотрудники",
        items=rows,
        search_field=search_field,
        search_query=search_query,
        search_error=search_error,
        focus_id=focus_id,
    )


@app.route("/admin/staff/new", methods=["GET", "POST"])
def admin_staff_new():
    if not require_admin():
        abort(403)
    departments = db.query(
        """
        SELECT d.id, d.name, mi.name AS institution_name
        FROM departments d
        JOIN medical_institutions mi ON mi.id = d.institution_id
        ORDER BY mi.name, d.name
        """
    )
    specializations = db.query("SELECT id, code, name FROM specializations ORDER BY name")
    form_data = {
        "department_id": "",
        "name": "",
        "phone": "",
        "email": "",
        "hire_date": date.today().isoformat(),
        "staff_type": "doctor",
        "is_active": "1",
        "inn": "",
        "experience_years": "",
        "license_number": "",
        "specialization_id": "",
    }
    error = ""
    if request.method == "POST":
        form_data = {k: request.form.get(k, "").strip() for k in form_data}
        department_id = parse_int(form_data["department_id"])
        experience_years = parse_int(form_data["experience_years"])
        specialization_id = parse_int(form_data["specialization_id"])
        staff_type = form_data["staff_type"]
        is_doctor = staff_type == "doctor"
        if not department_id:
            error = "Выберите отделение"
        elif not form_data["name"] or not form_data["phone"] or not form_data["email"] or not form_data["hire_date"] or not form_data["inn"]:
            error = "Заполните обязательные поля"
        elif is_doctor and (experience_years is None or experience_years < 0 or not form_data["license_number"] or not specialization_id):
            error = "Для врача укажите стаж, номер лицензии и специализацию"
        else:
            new_id = next_table_id("staff")
            db.execute(
                "INSERT INTO staff(id, department_id, name, phone, email, hire_date, staff_type, is_active, inn) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                [new_id, department_id, form_data["name"], form_data["phone"], form_data["email"], form_data["hire_date"], staff_type, parse_bool(form_data["is_active"]), form_data["inn"]],
            )
            if is_doctor:
                db.execute("INSERT INTO doctors(id, experience_years, license_number) VALUES (%s, %s, %s)", [new_id, experience_years, form_data["license_number"]])
                db.execute("INSERT INTO doctors_specializations(doctor_id, specialization_id) VALUES (%s, %s)", [new_id, specialization_id])
            flash(f"Сотрудник #{new_id} создан")
            return redirect(url_for("admin_staff_detail", staff_id=new_id))
    return render_admin(
        "admin_staff_form.html",
        title="Новый сотрудник",
        error=error,
        form_data=form_data,
        departments=departments,
        specializations=specializations,
        staff_type_choices=STAFF_TYPE_CHOICES,
        is_edit=False,
    )


@app.route("/admin/staff/<int:staff_id>")
def admin_staff_detail(staff_id):
    if not require_admin():
        abort(403)
    rows = db.query(
        """
        SELECT s.*, d.id AS department_id, d.name AS department_name, mi.id AS institution_id, mi.name AS institution_name,
               dr.experience_years, dr.license_number,
               (
                 SELECT sp.name
                 FROM doctors_specializations ds
                 JOIN specializations sp ON sp.id = ds.specialization_id
                 WHERE ds.doctor_id = s.id
                 ORDER BY ds.specialization_id
                 LIMIT 1
               ) AS specialization_name
        FROM staff s
        JOIN departments d ON d.id = s.department_id
        JOIN medical_institutions mi ON mi.id = d.institution_id
        LEFT JOIN doctors dr ON dr.id = s.id
        WHERE s.id = %s
        """,
        [staff_id],
    )
    if not rows:
        abort(404)
    item = rows[0]
    item["staff_type_ru"] = STAFF_TYPE_LABELS.get(item["staff_type"], item["staff_type"])
    return render_admin("admin_staff_detail.html", title=f"Сотрудник #{staff_id}", item=item)


@app.route("/admin/staff/<int:staff_id>/edit", methods=["GET", "POST"])
def admin_staff_edit(staff_id):
    if not require_admin():
        abort(403)
    rows = db.query(
        """
        SELECT s.*, dr.experience_years, dr.license_number, ds.specialization_id
        FROM staff s
        LEFT JOIN doctors dr ON dr.id = s.id
        LEFT JOIN LATERAL (
          SELECT specialization_id
          FROM doctors_specializations
          WHERE doctor_id = s.id
          ORDER BY specialization_id
          LIMIT 1
        ) ds ON true
        WHERE s.id = %s
        """,
        [staff_id],
    )
    if not rows:
        abort(404)
    current = rows[0]
    departments = db.query(
        """
        SELECT d.id, d.name, mi.name AS institution_name
        FROM departments d
        JOIN medical_institutions mi ON mi.id = d.institution_id
        ORDER BY mi.name, d.name
        """
    )
    specializations = db.query("SELECT id, code, name FROM specializations ORDER BY name")
    form_data = {
        "department_id": str(current["department_id"]),
        "name": current["name"],
        "phone": current["phone"],
        "email": current["email"],
        "hire_date": current["hire_date"].isoformat(),
        "staff_type": current["staff_type"],
        "is_active": "1" if current["is_active"] else "",
        "inn": current["inn"],
        "experience_years": "" if current["experience_years"] is None else str(current["experience_years"]),
        "license_number": "" if current["license_number"] is None else current["license_number"],
        "specialization_id": "" if current["specialization_id"] is None else str(current["specialization_id"]),
    }
    error = ""
    if request.method == "POST":
        form_data = {k: request.form.get(k, "").strip() for k in form_data}
        department_id = parse_int(form_data["department_id"])
        experience_years = parse_int(form_data["experience_years"])
        specialization_id = parse_int(form_data["specialization_id"])
        staff_type = form_data["staff_type"]
        is_doctor = staff_type == "doctor"
        if not department_id:
            error = "Выберите отделение"
        elif not form_data["name"] or not form_data["phone"] or not form_data["email"] or not form_data["hire_date"] or not form_data["inn"]:
            error = "Заполните обязательные поля"
        elif is_doctor and (experience_years is None or experience_years < 0 or not form_data["license_number"] or not specialization_id):
            error = "Для врача укажите стаж, номер лицензии и специализацию"
        elif not is_doctor and current["experience_years"] is not None and db.query("SELECT id FROM encounters WHERE doctor_id = %s LIMIT 1", [staff_id]):
            error = "Нельзя сменить тип врача, у которого уже есть приемы"
        else:
            db.execute(
                "UPDATE staff SET department_id=%s, name=%s, phone=%s, email=%s, hire_date=%s, staff_type=%s, is_active=%s, inn=%s WHERE id=%s",
                [department_id, form_data["name"], form_data["phone"], form_data["email"], form_data["hire_date"], staff_type, parse_bool(form_data["is_active"]), form_data["inn"], staff_id],
            )
            if is_doctor:
                if current["experience_years"] is None:
                    db.execute("INSERT INTO doctors(id, experience_years, license_number) VALUES (%s, %s, %s)", [staff_id, experience_years, form_data["license_number"]])
                else:
                    db.execute("UPDATE doctors SET experience_years=%s, license_number=%s WHERE id=%s", [experience_years, form_data["license_number"], staff_id])
                db.execute("DELETE FROM doctors_specializations WHERE doctor_id=%s", [staff_id])
                db.execute("INSERT INTO doctors_specializations(doctor_id, specialization_id) VALUES (%s, %s)", [staff_id, specialization_id])
            elif current["experience_years"] is not None:
                db.execute("DELETE FROM doctors_specializations WHERE doctor_id=%s", [staff_id])
                db.execute("DELETE FROM doctors WHERE id=%s", [staff_id])
            flash(f"Сотрудник #{staff_id} обновлен")
            return redirect(url_for("admin_staff_detail", staff_id=staff_id))
    return render_admin(
        "admin_staff_form.html",
        title=f"Редактировать сотрудника #{staff_id}",
        error=error,
        form_data=form_data,
        departments=departments,
        specializations=specializations,
        staff_type_choices=STAFF_TYPE_CHOICES,
        is_edit=True,
        item_id=staff_id,
    )


@app.route("/admin/institutions")
def admin_institutions_list():
    if not require_admin():
        abort(403)
    search_field = request.args.get("search_field", "").strip().lower()
    search_query = request.args.get("search_query", "").strip()
    if not search_query:
        search_query = request.args.get("search_query_text", "").strip()
    allowed_fields = {"id", "name", "type", "phone", "email"}
    patterns = {
        "id": r"^\d{1,10}$",
        "name": r"^.{2,120}$",
        "type": r"^.{2,60}$",
        "phone": r"^\+?[0-9\-\s\(\)]{6,22}$",
        "email": r"^[^\s@]+@[^\s@]+\.[^\s@]+$",
    }
    messages = {
        "id": "ID: только цифры",
        "name": "Название: минимум 2 символа",
        "type": "Тип: минимум 2 символа",
        "phone": "Телефон: допустимы цифры, +, пробелы, (), дефис",
        "email": "Email в формате name@example.com",
    }
    search_field, search_query, search_error = validate_admin_search(
        search_field, search_query, "name", allowed_fields, patterns, messages
    )
    focus_id = parse_int(request.args.get("focus", "").strip())
    if search_error:
        rows = []
    else:
        wildcard = f"%{search_query}%"
        rows = db.query(
            """
            SELECT mi.*,
                   (SELECT COUNT(*) FROM departments d WHERE d.institution_id = mi.id) AS departments_count
            FROM medical_institutions mi
            WHERE (
              %s = ''
              OR (%s = 'id' AND CAST(mi.id AS TEXT) = %s)
              OR (%s = 'name' AND LOWER(mi.name) LIKE LOWER(%s))
              OR (%s = 'type' AND LOWER(mi.type) LIKE LOWER(%s))
              OR (%s = 'phone' AND mi.phone LIKE %s)
              OR (%s = 'email' AND LOWER(mi.email) LIKE LOWER(%s))
            )
            ORDER BY mi.name, mi.id
            """,
            [
                search_query,
                search_field, search_query,
                search_field, wildcard,
                search_field, wildcard,
                search_field, wildcard,
                search_field, wildcard,
            ],
        )
    for row in rows:
        row["type_ru"] = INSTITUTION_TYPE_LABELS.get(row["type"], row["type"])
        row["is_focused"] = bool(focus_id) and row["id"] == focus_id
    return render_admin(
        "admin_institutions_list.html",
        title="Учреждения",
        items=rows,
        search_field=search_field,
        search_query=search_query,
        search_error=search_error,
        focus_id=focus_id,
    )


@app.route("/admin/institutions/new", methods=["GET", "POST"])
def admin_institutions_new():
    if not require_admin():
        abort(403)
    form_data = {"name": "", "type": "", "phone": "", "email": ""}
    error = ""
    if request.method == "POST":
        form_data = {k: request.form.get(k, "").strip() for k in form_data}
        if not all(form_data.values()):
            error = "Заполните обязательные поля"
        elif form_data["type"] not in INSTITUTION_TYPE_LABELS:
            error = "Выберите тип учреждения из списка"
        else:
            new_id = next_table_id("medical_institutions")
            db.execute(
                "INSERT INTO medical_institutions(id, name, type, phone, email) VALUES (%s, %s, %s, %s, %s)",
                [new_id, form_data["name"], form_data["type"], form_data["phone"], form_data["email"]],
            )
            flash(f"Учреждение #{new_id} создано")
            return redirect(url_for("admin_institution_detail", institution_id=new_id))
    return render_admin(
        "admin_institution_form.html",
        title="Новое учреждение",
        error=error,
        form_data=form_data,
        institution_type_choices=INSTITUTION_TYPE_CHOICES,
        is_edit=False,
    )


@app.route("/admin/institutions/<int:institution_id>")
def admin_institution_detail(institution_id):
    if not require_admin():
        abort(403)
    rows = db.query(
        """
        SELECT mi.*,
               (SELECT COUNT(*) FROM departments d WHERE d.institution_id = mi.id) AS departments_count
        FROM medical_institutions mi
        WHERE mi.id = %s
        """,
        [institution_id],
    )
    if not rows:
        abort(404)
    item = rows[0]
    item["type_ru"] = INSTITUTION_TYPE_LABELS.get(item["type"], item["type"])
    departments = db.query("SELECT id, name, type, phone FROM departments WHERE institution_id = %s ORDER BY name", [institution_id])
    for row in departments:
        row["type_ru"] = DEPARTMENT_TYPE_LABELS.get(row["type"], row["type"])
    return render_admin("admin_institution_detail.html", title=f"Учреждение #{institution_id}", item=item, departments=departments)


@app.route("/admin/institutions/<int:institution_id>/edit", methods=["GET", "POST"])
def admin_institution_edit(institution_id):
    if not require_admin():
        abort(403)
    rows = db.query("SELECT * FROM medical_institutions WHERE id = %s", [institution_id])
    if not rows:
        abort(404)
    current = rows[0]
    form_data = {"name": current["name"], "type": current["type"], "phone": current["phone"], "email": current["email"]}
    error = ""
    if request.method == "POST":
        form_data = {k: request.form.get(k, "").strip() for k in form_data}
        if not all(form_data.values()):
            error = "Заполните обязательные поля"
        elif form_data["type"] not in INSTITUTION_TYPE_LABELS:
            error = "Выберите тип учреждения из списка"
        else:
            db.execute("UPDATE medical_institutions SET name=%s, type=%s, phone=%s, email=%s WHERE id=%s", [form_data["name"], form_data["type"], form_data["phone"], form_data["email"], institution_id])
            flash(f"Учреждение #{institution_id} обновлено")
            return redirect(url_for("admin_institution_detail", institution_id=institution_id))
    return render_admin(
        "admin_institution_form.html",
        title=f"Редактировать учреждение #{institution_id}",
        error=error,
        form_data=form_data,
        institution_type_choices=INSTITUTION_TYPE_CHOICES,
        is_edit=True,
        item_id=institution_id,
    )


@app.route("/admin/departments")
def admin_departments_list():
    if not require_admin():
        abort(403)
    search_field = request.args.get("search_field", "").strip().lower()
    search_query = request.args.get("search_query", "").strip()
    if not search_query:
        search_query = request.args.get("search_query_text", "").strip()
    allowed_fields = {"id", "name", "institution", "type", "phone"}
    patterns = {
        "id": r"^\d{1,10}$",
        "name": r"^.{2,120}$",
        "institution": r"^.{2,120}$",
        "type": r"^.{2,60}$",
        "phone": r"^\+?[0-9\-\s\(\)]{6,22}$",
    }
    messages = {
        "id": "ID: только цифры",
        "name": "Название: минимум 2 символа",
        "institution": "Учреждение: минимум 2 символа",
        "type": "Тип: минимум 2 символа",
        "phone": "Телефон: допустимы цифры, +, пробелы, (), дефис",
    }
    search_field, search_query, search_error = validate_admin_search(
        search_field, search_query, "name", allowed_fields, patterns, messages
    )
    focus_id = parse_int(request.args.get("focus", "").strip())
    if search_error:
        rows = []
    else:
        wildcard = f"%{search_query}%"
        rows = db.query(
            """
            SELECT d.*, mi.id AS institution_id, mi.name AS institution_name,
                   (SELECT COUNT(*) FROM staff s WHERE s.department_id = d.id) AS staff_count
            FROM departments d
            JOIN medical_institutions mi ON mi.id = d.institution_id
            WHERE (
              %s = ''
              OR (%s = 'id' AND CAST(d.id AS TEXT) = %s)
              OR (%s = 'name' AND LOWER(d.name) LIKE LOWER(%s))
              OR (%s = 'institution' AND LOWER(mi.name) LIKE LOWER(%s))
              OR (%s = 'type' AND LOWER(d.type) LIKE LOWER(%s))
              OR (%s = 'phone' AND d.phone LIKE %s)
            )
            ORDER BY mi.name, d.name, d.id
            """,
            [
                search_query,
                search_field, search_query,
                search_field, wildcard,
                search_field, wildcard,
                search_field, wildcard,
                search_field, wildcard,
            ],
        )
    for row in rows:
        row["type_ru"] = DEPARTMENT_TYPE_LABELS.get(row["type"], row["type"])
        row["is_focused"] = bool(focus_id) and row["id"] == focus_id
    return render_admin(
        "admin_departments_list.html",
        title="Отделения",
        items=rows,
        search_field=search_field,
        search_query=search_query,
        search_error=search_error,
        focus_id=focus_id,
    )


@app.route("/admin/departments/new", methods=["GET", "POST"])
def admin_departments_new():
    if not require_admin():
        abort(403)
    institutions = db.query("SELECT id, name FROM medical_institutions ORDER BY name")
    form_data = {"name": "", "phone": "", "type": "", "institution_id": ""}
    error = ""
    if request.method == "POST":
        form_data = {k: request.form.get(k, "").strip() for k in form_data}
        institution_id = parse_int(form_data["institution_id"])
        if not institution_id or not form_data["name"] or not form_data["phone"] or not form_data["type"]:
            error = "Заполните обязательные поля"
        elif form_data["type"] not in DEPARTMENT_TYPE_LABELS:
            error = "Выберите тип отделения из списка"
        else:
            new_id = next_table_id("departments")
            db.execute("INSERT INTO departments(id, name, phone, type, institution_id) VALUES (%s, %s, %s, %s, %s)", [new_id, form_data["name"], form_data["phone"], form_data["type"], institution_id])
            flash(f"Отделение #{new_id} создано")
            return redirect(url_for("admin_department_detail", department_id=new_id))
    return render_admin(
        "admin_department_form.html",
        title="Новое отделение",
        error=error,
        form_data=form_data,
        institutions=institutions,
        department_type_choices=DEPARTMENT_TYPE_CHOICES,
        is_edit=False,
    )


@app.route("/admin/departments/<int:department_id>")
def admin_department_detail(department_id):
    if not require_admin():
        abort(403)
    rows = db.query(
        """
        SELECT d.*, mi.id AS institution_id, mi.name AS institution_name
        FROM departments d
        JOIN medical_institutions mi ON mi.id = d.institution_id
        WHERE d.id = %s
        """,
        [department_id],
    )
    if not rows:
        abort(404)
    item = rows[0]
    item["type_ru"] = DEPARTMENT_TYPE_LABELS.get(item["type"], item["type"])
    staff_rows = db.query("SELECT id, name, staff_type, phone, email FROM staff WHERE department_id=%s ORDER BY name", [department_id])
    for row in staff_rows:
        row["staff_type_ru"] = STAFF_TYPE_LABELS.get(row["staff_type"], row["staff_type"])
    return render_admin("admin_department_detail.html", title=f"Отделение #{department_id}", item=item, staff_rows=staff_rows)


@app.route("/admin/departments/<int:department_id>/edit", methods=["GET", "POST"])
def admin_department_edit(department_id):
    if not require_admin():
        abort(403)
    rows = db.query("SELECT * FROM departments WHERE id = %s", [department_id])
    if not rows:
        abort(404)
    current = rows[0]
    institutions = db.query("SELECT id, name FROM medical_institutions ORDER BY name")
    form_data = {"name": current["name"], "phone": current["phone"], "type": current["type"], "institution_id": str(current["institution_id"])}
    error = ""
    if request.method == "POST":
        form_data = {k: request.form.get(k, "").strip() for k in form_data}
        institution_id = parse_int(form_data["institution_id"])
        if not institution_id or not form_data["name"] or not form_data["phone"] or not form_data["type"]:
            error = "Заполните обязательные поля"
        elif form_data["type"] not in DEPARTMENT_TYPE_LABELS:
            error = "Выберите тип отделения из списка"
        else:
            db.execute("UPDATE departments SET name=%s, phone=%s, type=%s, institution_id=%s WHERE id=%s", [form_data["name"], form_data["phone"], form_data["type"], institution_id, department_id])
            flash(f"Отделение #{department_id} обновлено")
            return redirect(url_for("admin_department_detail", department_id=department_id))
    return render_admin(
        "admin_department_form.html",
        title=f"Редактировать отделение #{department_id}",
        error=error,
        form_data=form_data,
        institutions=institutions,
        department_type_choices=DEPARTMENT_TYPE_CHOICES,
        is_edit=True,
        item_id=department_id,
    )


@app.route("/admin/patients")
def admin_patients_list():
    if not require_admin():
        abort(403)
    search_field = request.args.get("search_field", "").strip().lower()
    search_query = request.args.get("search_query", "").strip()
    if not search_query:
        search_query = request.args.get("search_query_text", "").strip()
    allowed_fields = {"id", "name", "phone", "email", "snus", "passport"}
    patterns = {
        "id": r"^\d{1,10}$",
        "name": r"^[A-Za-zА-Яа-яЁё\s\-]{2,120}$",
        "phone": r"^\+?[0-9\-\s\(\)]{6,22}$",
        "email": r"^[^\s@]+@[^\s@]+\.[^\s@]+$",
        "snus": r"^[0-9\-\s]{8,20}$",
        "passport": r"^\d{4}\s?\d{6}$",
    }
    messages = {
        "id": "ID: только цифры",
        "name": "ФИО: минимум 2 символа, буквы/пробел/дефис",
        "phone": "Телефон: допустимы цифры, +, пробелы, (), дефис",
        "email": "Email в формате name@example.com",
        "snus": "СНИЛС: только цифры, пробелы, дефис",
        "passport": "Паспорт: 10 цифр, формат 4515 100155",
    }
    search_field, search_query, search_error = validate_admin_search(
        search_field, search_query, "name", allowed_fields, patterns, messages
    )
    focus_id = parse_int(request.args.get("focus", "").strip())
    if search_error:
        rows = []
    else:
        wildcard = f"%{search_query}%"
        rows = db.query(
            """
            SELECT p.*,
                   (SELECT COUNT(*) FROM encounters e WHERE e.patient_id = p.id) AS encounters_count
            FROM patients p
            WHERE (
              %s = ''
              OR (%s = 'id' AND CAST(p.id AS TEXT) = %s)
              OR (%s = 'name' AND LOWER(p.name) LIKE LOWER(%s))
              OR (%s = 'phone' AND p.phone LIKE %s)
              OR (%s = 'email' AND LOWER(p.email) LIKE LOWER(%s))
              OR (%s = 'snus' AND p.snus LIKE %s)
              OR (%s = 'passport' AND p.passport LIKE %s)
            )
            ORDER BY p.name, p.id
            """,
            [
                search_query,
                search_field, search_query,
                search_field, wildcard,
                search_field, wildcard,
                search_field, wildcard,
                search_field, wildcard,
                search_field, wildcard,
            ],
        )
    for row in rows:
        row["is_focused"] = bool(focus_id) and row["id"] == focus_id
    return render_admin(
        "admin_patients_list.html",
        title="Пациенты",
        items=rows,
        search_field=search_field,
        search_query=search_query,
        search_error=search_error,
        focus_id=focus_id,
    )


@app.route("/admin/patients/new", methods=["GET", "POST"])
def admin_patients_new():
    if not require_admin():
        abort(403)
    form_data = {"name": "", "sex": "", "phone": "", "email": "", "snus": "", "passport": "", "birth_date": ""}
    error = ""
    if request.method == "POST":
        form_data = {k: request.form.get(k, "").strip() for k in form_data}
        if not all(form_data.values()):
            error = "Заполните обязательные поля"
        elif form_data["sex"] not in {"M", "F"}:
            error = "Пол: выберите М или Ж"
        else:
            new_id = next_table_id("patients")
            db.execute(
                "INSERT INTO patients(id, name, sex, phone, email, snus, passport, birth_date) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                [new_id, form_data["name"], form_data["sex"], form_data["phone"], form_data["email"], form_data["snus"], form_data["passport"], form_data["birth_date"]],
            )
            flash(f"Пациент #{new_id} создан")
            return redirect(url_for("admin_patient_detail", patient_id=new_id))
    return render_admin("admin_patient_form.html", title="Новый пациент", error=error, form_data=form_data, is_edit=False)


@app.route("/admin/patients/<int:patient_id>")
def admin_patient_detail(patient_id):
    if not require_admin():
        abort(403)
    rows = db.query("SELECT * FROM patients WHERE id = %s", [patient_id])
    if not rows:
        abort(404)
    item = rows[0]
    encounters = db.query(
        """
        SELECT e.id, e.type, e.start_datetime, e.end_datetime, s.id AS doctor_id, s.name AS doctor_name
        FROM encounters e
        JOIN staff s ON s.id = e.doctor_id
        WHERE e.patient_id = %s
        ORDER BY e.start_datetime DESC
        """,
        [patient_id],
    )
    for row in encounters:
        row["type_ru"] = ENCOUNTER_TYPE_LABELS.get(row["type"], row["type"])
    return render_admin("admin_patient_detail.html", title=f"Пациент #{patient_id}", item=item, encounters=encounters)


@app.route("/admin/patients/<int:patient_id>/edit", methods=["GET", "POST"])
def admin_patient_edit(patient_id):
    if not require_admin():
        abort(403)
    rows = db.query("SELECT * FROM patients WHERE id = %s", [patient_id])
    if not rows:
        abort(404)
    current = rows[0]
    form_data = {k: str(current[k]) if k == "birth_date" else current[k] for k in ["name", "sex", "phone", "email", "snus", "passport", "birth_date"]}
    if isinstance(current["birth_date"], date):
        form_data["birth_date"] = current["birth_date"].isoformat()
    error = ""
    if request.method == "POST":
        form_data = {k: request.form.get(k, "").strip() for k in form_data}
        if not all(form_data.values()):
            error = "Заполните обязательные поля"
        elif form_data["sex"] not in {"M", "F"}:
            error = "Пол: выберите М или Ж"
        else:
            db.execute(
                "UPDATE patients SET name=%s, sex=%s, phone=%s, email=%s, snus=%s, passport=%s, birth_date=%s WHERE id=%s",
                [form_data["name"], form_data["sex"], form_data["phone"], form_data["email"], form_data["snus"], form_data["passport"], form_data["birth_date"], patient_id],
            )
            flash(f"Пациент #{patient_id} обновлен")
            return redirect(url_for("admin_patient_detail", patient_id=patient_id))
    return render_admin("admin_patient_form.html", title=f"Редактировать пациента #{patient_id}", error=error, form_data=form_data, is_edit=True, item_id=patient_id)


@app.route("/admin/medications")
def admin_medications_list():
    if not require_admin():
        abort(403)
    search_field = request.args.get("search_field", "").strip().lower()
    search_query = request.args.get("search_query", "").strip()
    if not search_query:
        search_query = request.args.get("search_query_text", "").strip()
    allowed_fields = {"id", "name", "form", "strength"}
    patterns = {
        "id": r"^\d{1,10}$",
        "name": r"^.{2,120}$",
        "form": r"^.{2,60}$",
        "strength": r"^.{1,60}$",
    }
    messages = {
        "id": "ID: только цифры",
        "name": "Название: минимум 2 символа",
        "form": "Форма: минимум 2 символа",
        "strength": "Дозировка: минимум 1 символ",
    }
    search_field, search_query, search_error = validate_admin_search(
        search_field, search_query, "name", allowed_fields, patterns, messages
    )
    focus_id = parse_int(request.args.get("focus", "").strip())
    if search_error:
        rows = []
    else:
        wildcard = f"%{search_query}%"
        rows = db.query(
            """
            SELECT m.*,
                   (SELECT COUNT(*) FROM treatment_items ti WHERE ti.medication_id = m.id) AS usage_count
            FROM medication m
            WHERE (
              %s = ''
              OR (%s = 'id' AND CAST(m.id AS TEXT) = %s)
              OR (%s = 'name' AND LOWER(m.name) LIKE LOWER(%s))
              OR (%s = 'form' AND LOWER(m.form) LIKE LOWER(%s))
              OR (%s = 'strength' AND LOWER(m.strength) LIKE LOWER(%s))
            )
            ORDER BY m.name, m.id
            """,
            [
                search_query,
                search_field, search_query,
                search_field, wildcard,
                search_field, wildcard,
                search_field, wildcard,
            ],
        )
    for row in rows:
        row["is_focused"] = bool(focus_id) and row["id"] == focus_id
    return render_admin(
        "admin_medications_list.html",
        title="Препараты",
        items=rows,
        search_field=search_field,
        search_query=search_query,
        search_error=search_error,
        focus_id=focus_id,
    )


@app.route("/admin/medications/new", methods=["GET", "POST"])
def admin_medications_new():
    if not require_admin():
        abort(403)
    form_data = {"name": "", "form": "", "strength": ""}
    error = ""
    if request.method == "POST":
        form_data = {k: request.form.get(k, "").strip() for k in form_data}
        if not all(form_data.values()):
            error = "Заполните обязательные поля"
        else:
            new_id = next_table_id("medication")
            db.execute("INSERT INTO medication(id, name, form, strength) VALUES (%s, %s, %s, %s)", [new_id, form_data["name"], form_data["form"], form_data["strength"]])
            flash(f"Препарат #{new_id} создан")
            return redirect(url_for("admin_medication_detail", medication_id=new_id))
    return render_admin("admin_medication_form.html", title="Новый препарат", error=error, form_data=form_data, is_edit=False)


@app.route("/admin/medications/<int:medication_id>")
def admin_medication_detail(medication_id):
    if not require_admin():
        abort(403)
    rows = db.query("SELECT * FROM medication WHERE id = %s", [medication_id])
    if not rows:
        abort(404)
    item = rows[0]
    usages = db.query(
        """
        SELECT ti.id, ti.encounter_id, ti.start_date, ti.end_date, p.name AS patient_name, p.id AS patient_id
        FROM treatment_items ti
        JOIN encounters e ON e.id = ti.encounter_id
        JOIN patients p ON p.id = e.patient_id
        WHERE ti.medication_id = %s
        ORDER BY ti.start_date DESC, ti.id DESC
        LIMIT 30
        """,
        [medication_id],
    )
    return render_admin("admin_medication_detail.html", title=f"Препарат #{medication_id}", item=item, usages=usages)


@app.route("/admin/medications/<int:medication_id>/edit", methods=["GET", "POST"])
def admin_medication_edit(medication_id):
    if not require_admin():
        abort(403)
    rows = db.query("SELECT * FROM medication WHERE id = %s", [medication_id])
    if not rows:
        abort(404)
    current = rows[0]
    form_data = {"name": current["name"], "form": current["form"], "strength": current["strength"]}
    error = ""
    if request.method == "POST":
        form_data = {k: request.form.get(k, "").strip() for k in form_data}
        if not all(form_data.values()):
            error = "Заполните обязательные поля"
        else:
            db.execute("UPDATE medication SET name=%s, form=%s, strength=%s WHERE id=%s", [form_data["name"], form_data["form"], form_data["strength"], medication_id])
            flash(f"Препарат #{medication_id} обновлен")
            return redirect(url_for("admin_medication_detail", medication_id=medication_id))
    return render_admin("admin_medication_form.html", title=f"Редактировать препарат #{medication_id}", error=error, form_data=form_data, is_edit=True, item_id=medication_id)


@app.route("/admin/procedures")
def admin_procedures_list():
    if not require_admin():
        abort(403)
    search_field = request.args.get("search_field", "").strip().lower()
    search_query = request.args.get("search_query", "").strip()
    if not search_query:
        search_query = request.args.get("search_query_text", "").strip()
    allowed_fields = {"id", "code", "name", "duration"}
    patterns = {
        "id": r"^\d{1,10}$",
        "code": r"^[A-Za-z0-9\-_]{2,40}$",
        "name": r"^.{2,120}$",
        "duration": r"^\d{1,5}$",
    }
    messages = {
        "id": "ID: только цифры",
        "code": "Код: буквы, цифры, дефис, подчеркивание",
        "name": "Название: минимум 2 символа",
        "duration": "Длительность: только цифры",
    }
    search_field, search_query, search_error = validate_admin_search(
        search_field, search_query, "name", allowed_fields, patterns, messages
    )
    focus_id = parse_int(request.args.get("focus", "").strip())
    if search_error:
        rows = []
    else:
        wildcard = f"%{search_query}%"
        rows = db.query(
            """
            SELECT p.*,
                   (SELECT COUNT(*) FROM treatment_items ti WHERE ti.procedure_id = p.id) AS usage_count
            FROM procedures p
            WHERE (
              %s = ''
              OR (%s = 'id' AND CAST(p.id AS TEXT) = %s)
              OR (%s = 'code' AND LOWER(p.code) LIKE LOWER(%s))
              OR (%s = 'name' AND LOWER(p.name) LIKE LOWER(%s))
              OR (%s = 'duration' AND CAST(p.default_duration_min AS TEXT) = %s)
            )
            ORDER BY p.name, p.id
            """,
            [
                search_query,
                search_field, search_query,
                search_field, wildcard,
                search_field, wildcard,
                search_field, search_query,
            ],
        )
    for row in rows:
        row["is_focused"] = bool(focus_id) and row["id"] == focus_id
    return render_admin(
        "admin_procedures_list.html",
        title="Процедуры",
        items=rows,
        search_field=search_field,
        search_query=search_query,
        search_error=search_error,
        focus_id=focus_id,
    )


@app.route("/admin/procedures/new", methods=["GET", "POST"])
def admin_procedures_new():
    if not require_admin():
        abort(403)
    form_data = {"code": "", "name": "", "default_duration_min": ""}
    error = ""
    if request.method == "POST":
        form_data = {k: request.form.get(k, "").strip() for k in form_data}
        duration = parse_int(form_data["default_duration_min"])
        if not form_data["code"] or not form_data["name"] or duration is None or duration <= 0:
            error = "Заполните обязательные поля (длительность > 0)"
        else:
            new_id = next_table_id("procedures")
            db.execute("INSERT INTO procedures(id, code, name, default_duration_min) VALUES (%s, %s, %s, %s)", [new_id, form_data["code"], form_data["name"], duration])
            flash(f"Процедура #{new_id} создана")
            return redirect(url_for("admin_procedure_detail", procedure_id=new_id))
    return render_admin("admin_procedure_form.html", title="Новая процедура", error=error, form_data=form_data, is_edit=False)


@app.route("/admin/procedures/<int:procedure_id>")
def admin_procedure_detail(procedure_id):
    if not require_admin():
        abort(403)
    rows = db.query("SELECT * FROM procedures WHERE id = %s", [procedure_id])
    if not rows:
        abort(404)
    item = rows[0]
    usages = db.query(
        """
        SELECT ti.id, ti.encounter_id, ti.start_date, ti.end_date, p.name AS patient_name, p.id AS patient_id
        FROM treatment_items ti
        JOIN encounters e ON e.id = ti.encounter_id
        JOIN patients p ON p.id = e.patient_id
        WHERE ti.procedure_id = %s
        ORDER BY ti.start_date DESC, ti.id DESC
        LIMIT 30
        """,
        [procedure_id],
    )
    return render_admin("admin_procedure_detail.html", title=f"Процедура #{procedure_id}", item=item, usages=usages)


@app.route("/admin/procedures/<int:procedure_id>/edit", methods=["GET", "POST"])
def admin_procedure_edit(procedure_id):
    if not require_admin():
        abort(403)
    rows = db.query("SELECT * FROM procedures WHERE id = %s", [procedure_id])
    if not rows:
        abort(404)
    current = rows[0]
    form_data = {"code": current["code"], "name": current["name"], "default_duration_min": str(current["default_duration_min"])}
    error = ""
    if request.method == "POST":
        form_data = {k: request.form.get(k, "").strip() for k in form_data}
        duration = parse_int(form_data["default_duration_min"])
        if not form_data["code"] or not form_data["name"] or duration is None or duration <= 0:
            error = "Заполните обязательные поля (длительность > 0)"
        else:
            db.execute("UPDATE procedures SET code=%s, name=%s, default_duration_min=%s WHERE id=%s", [form_data["code"], form_data["name"], duration, procedure_id])
            flash(f"Процедура #{procedure_id} обновлена")
            return redirect(url_for("admin_procedure_detail", procedure_id=procedure_id))
    return render_admin("admin_procedure_form.html", title=f"Редактировать процедуру #{procedure_id}", error=error, form_data=form_data, is_edit=True, item_id=procedure_id)


@app.route("/admin/specializations")
def admin_specializations_list():
    if not require_admin():
        abort(403)
    search_field = request.args.get("search_field", "").strip().lower()
    search_query = request.args.get("search_query", "").strip()
    if not search_query:
        search_query = request.args.get("search_query_text", "").strip()
    allowed_fields = {"id", "code", "name"}
    patterns = {
        "id": r"^\d{1,10}$",
        "code": r"^[A-Za-z0-9\-_]{2,40}$",
        "name": r"^.{2,120}$",
    }
    messages = {
        "id": "ID: только цифры",
        "code": "Код: буквы, цифры, дефис, подчеркивание",
        "name": "Название: минимум 2 символа",
    }
    search_field, search_query, search_error = validate_admin_search(
        search_field, search_query, "name", allowed_fields, patterns, messages
    )
    focus_id = parse_int(request.args.get("focus", "").strip())
    if search_error:
        rows = []
    else:
        wildcard = f"%{search_query}%"
        rows = db.query(
            """
            SELECT sp.*,
                   (SELECT COUNT(*) FROM doctors_specializations ds WHERE ds.specialization_id = sp.id) AS doctors_count
            FROM specializations sp
            WHERE (
              %s = ''
              OR (%s = 'id' AND CAST(sp.id AS TEXT) = %s)
              OR (%s = 'code' AND LOWER(sp.code) LIKE LOWER(%s))
              OR (%s = 'name' AND LOWER(sp.name) LIKE LOWER(%s))
            )
            ORDER BY sp.name, sp.id
            """,
            [
                search_query,
                search_field, search_query,
                search_field, wildcard,
                search_field, wildcard,
            ],
        )
    for row in rows:
        row["is_focused"] = bool(focus_id) and row["id"] == focus_id
    return render_admin(
        "admin_specializations_list.html",
        title="Специализации",
        items=rows,
        search_field=search_field,
        search_query=search_query,
        search_error=search_error,
        focus_id=focus_id,
    )


@app.route("/admin/specializations/new", methods=["GET", "POST"])
def admin_specializations_new():
    if not require_admin():
        abort(403)
    form_data = {"code": "", "name": ""}
    error = ""
    if request.method == "POST":
        form_data = {k: request.form.get(k, "").strip() for k in form_data}
        if not form_data["code"] or not form_data["name"]:
            error = "Заполните обязательные поля"
        elif not re.fullmatch(r"^[A-Za-z0-9\-_]{2,40}$", form_data["code"]):
            error = "Код: буквы, цифры, дефис, подчеркивание"
        else:
            new_id = next_table_id("specializations")
            db.execute("INSERT INTO specializations(id, code, name) VALUES (%s, %s, %s)", [new_id, form_data["code"], form_data["name"]])
            flash(f"Специализация #{new_id} создана")
            return redirect(url_for("admin_specializations_list", focus=new_id))
    return render_admin("admin_specialization_form.html", title="Новая специализация", error=error, form_data=form_data, is_edit=False)


@app.route("/admin/specializations/<int:specialization_id>/edit", methods=["GET", "POST"])
def admin_specializations_edit(specialization_id):
    if not require_admin():
        abort(403)
    rows = db.query("SELECT * FROM specializations WHERE id = %s", [specialization_id])
    if not rows:
        abort(404)
    current = rows[0]
    form_data = {"code": current["code"], "name": current["name"]}
    error = ""
    if request.method == "POST":
        form_data = {k: request.form.get(k, "").strip() for k in form_data}
        if not form_data["code"] or not form_data["name"]:
            error = "Заполните обязательные поля"
        elif not re.fullmatch(r"^[A-Za-z0-9\-_]{2,40}$", form_data["code"]):
            error = "Код: буквы, цифры, дефис, подчеркивание"
        else:
            db.execute("UPDATE specializations SET code=%s, name=%s WHERE id=%s", [form_data["code"], form_data["name"], specialization_id])
            flash(f"Специализация #{specialization_id} обновлена")
            return redirect(url_for("admin_specializations_list", focus=specialization_id))
    return render_admin("admin_specialization_form.html", title=f"Редактировать специализацию #{specialization_id}", error=error, form_data=form_data, is_edit=True, item_id=specialization_id)


init_db()
SELECTS = load_selects(SQL_DIR / "02_selects.sql")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("APP_PORT", "5050")))
