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
    seed_check = db.query("SELECT COUNT(*) AS cnt FROM medical_institutions")
    if seed_check and int(seed_check[0]["cnt"]) == 0:
        db.execute_script_file(SQL_DIR / "01_seed.sql")
    ensure_demo_data()


def require_doctor():
    return session.get("role") == "doctor" and bool(session.get("doctor_id"))


def require_patient():
    return session.get("role") == "patient" and bool(session.get("patient_id"))


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


def doctor_nav():
    return [
        (url_for("doctor_my_patients"), "Мои пациенты"),
        (url_for("doctor_create_encounter"), "Новый прием"),
        (url_for("logout"), "Выход"),
    ]


def patient_nav():
    return [
        (url_for("patient_encounters"), "Мои приемы"),
        (url_for("patient_treatments"), "Мои назначения"),
        (url_for("logout"), "Выход"),
    ]


def render_doctor(template_name, **context):
    return render_template(template_name, nav_links=doctor_nav(), **context)


def render_patient(template_name, **context):
    return render_template(template_name, nav_links=patient_nav(), **context)


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
    if request.method == "POST":
        role = request.form.get("role", "").strip()
        user_id_raw = request.form.get("user_id", "").strip()
        if role not in {"doctor", "patient"}:
            error = "Выберите роль"
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
    return render_template("login.html", error=error, nav_links=[], brand_link=False)


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
            flash(f"Прием #{new_id} создан")
            return redirect(url_for("doctor_patient", patient_id=cleaned["patient_id"]))
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
    return render_patient(
        "patient_encounters.html",
        title="Мои приемы",
        encounters=rows,
        search_field=search_field,
        search_query=search_query,
        search_error=search_error,
        date_from=date_from,
        date_to=date_to,
        encounter_type_choices=ENCOUNTER_TYPE_CHOICES,
    )


@app.route("/patient/treatments")
def patient_treatments():
    if not require_patient():
        abort(403)
    only_active = request.args.get("only_active", "").strip() == "1"
    rows = db.query(SELECTS["PATIENT_TREATMENTS"], [session["patient_id"]])
    today = date.today()
    normalized_rows = []
    for row in rows:
        row["frequency_ru"] = FREQUENCY_LABELS.get(row["frequency"], row["frequency"])
        row["type_ru"] = ENCOUNTER_TYPE_LABELS.get(row["encounter_type"], row["encounter_type"])
        row["assignment_type_ru"] = ASSIGNMENT_TYPE_LABELS.get(row["type"], row["type"])
        row["is_expired"] = row["end_date"] < today
        if only_active and row["is_expired"]:
            continue
        normalized_rows.append(row)
    return render_patient(
        "patient_treatments.html",
        title="Мои назначения",
        treatments=normalized_rows,
        only_active=only_active,
    )


init_db()
SELECTS = load_selects(SQL_DIR / "02_selects.sql")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("APP_PORT", "5050")))
