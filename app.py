import os
import re
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session, abort
import db


BASE_DIR = Path(__file__).resolve().parent
SQL_DIR = BASE_DIR / "sql"

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "local-secret-key")


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


def init_db():
    db.execute_script_file(SQL_DIR / "00_create.sql")
    db.execute_script_file(SQL_DIR / "03_procedures.sql")
    db.execute_script_file(SQL_DIR / "04_triggers.sql")
    seed_check = db.query("SELECT COUNT(*) AS cnt FROM medical_institutions")
    if seed_check and int(seed_check[0]["cnt"]) == 0:
        db.execute_script_file(SQL_DIR / "01_seed.sql")


def require_doctor():
    if session.get("role") != "doctor" or not session.get("doctor_id"):
        return False
    return True


def require_patient():
    if session.get("role") != "patient" or not session.get("patient_id"):
        return False
    return True


def parse_dt(value):
    if not value:
        return None
    return datetime.fromisoformat(value)


def next_encounter_id():
    rows = db.query(SELECTS["NEXT_ENCOUNTER_ID"])
    return int(rows[0]["id"])


def next_treatment_id():
    rows = db.query(SELECTS["NEXT_TREATMENT_ID"])
    return int(rows[0]["id"])


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
            try:
                user_id = int(user_id_raw)
            except ValueError:
                error = "ID должен быть числом"
                user_id = None
            if user_id is not None:
                if role == "doctor":
                    exists = db.query(SELECTS["AUTH_DOCTOR_EXISTS"], [user_id])
                    if exists:
                        session.clear()
                        session["role"] = "doctor"
                        session["doctor_id"] = user_id
                        return redirect(url_for("doctor_my_patients"))
                    error = "Врач не найден"
                if role == "patient":
                    exists = db.query(SELECTS["AUTH_PATIENT_EXISTS"], [user_id])
                    if exists:
                        session.clear()
                        session["role"] = "patient"
                        session["patient_id"] = user_id
                        return redirect(url_for("patient_encounters"))
                    error = "Пациент не найден"
    return render_template("login.html", error=error)


@app.route("/doctor/create_encounter", methods=["GET", "POST"])
def doctor_create_encounter():
    if not require_doctor():
        abort(403)
    error = ""
    success = ""
    if request.method == "POST":
        patient_id_raw = request.form.get("patient_id", "").strip()
        bed_id_raw = request.form.get("bed_id", "").strip()
        encounter_type = request.form.get("type", "").strip()
        start_raw = request.form.get("start_datetime", "").strip()
        end_raw = request.form.get("end_datetime", "").strip()
        try:
            patient_id = int(patient_id_raw)
        except ValueError:
            patient_id = None
        bed_id = None
        if bed_id_raw:
            try:
                bed_id = int(bed_id_raw)
            except ValueError:
                bed_id = None
        try:
            start_dt = parse_dt(start_raw)
            end_dt = parse_dt(end_raw)
        except ValueError:
            start_dt = None
            end_dt = None
        if not patient_id:
            error = "Некорректный patient_id"
        elif not encounter_type:
            error = "Заполните type"
        elif not start_dt or not end_dt:
            error = "Некорректные даты"
        elif start_dt > end_dt:
            error = "start_datetime должен быть <= end_datetime"
        else:
            patient_exists = db.query(SELECTS["PATIENT_EXISTS"], [patient_id])
            if not patient_exists:
                error = "Пациент не найден"
            elif bed_id_raw and not db.query(SELECTS["BED_EXISTS"], [bed_id]):
                error = "Койка не найдена"
            else:
                new_id = next_encounter_id()
                db.execute(
                    "INSERT INTO encounters(id, patient_id, doctor_id, bed_id, type, start_datetime, end_datetime) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    [new_id, patient_id, session["doctor_id"], bed_id, encounter_type, start_dt, end_dt],
                )
                success = f"Прием создан, id={new_id}"
    return render_template("doctor_create_encounter.html", error=error, success=success)


@app.route("/doctor/edit_encounter/<int:encounter_id>", methods=["GET", "POST"])
def doctor_edit_encounter(encounter_id):
    if not require_doctor():
        abort(403)
    own = db.query(SELECTS["DOCTOR_OWN_ENCOUNTER_BY_ID"], [encounter_id, session["doctor_id"]])
    if not own:
        abort(404)
    row = own[0]
    error = ""
    success = ""
    if request.method == "POST":
        patient_id_raw = request.form.get("patient_id", "").strip()
        bed_id_raw = request.form.get("bed_id", "").strip()
        encounter_type = request.form.get("type", "").strip()
        start_raw = request.form.get("start_datetime", "").strip()
        end_raw = request.form.get("end_datetime", "").strip()
        try:
            patient_id = int(patient_id_raw)
        except ValueError:
            patient_id = None
        bed_id = None
        if bed_id_raw:
            try:
                bed_id = int(bed_id_raw)
            except ValueError:
                bed_id = None
        try:
            start_dt = parse_dt(start_raw)
            end_dt = parse_dt(end_raw)
        except ValueError:
            start_dt = None
            end_dt = None
        if not patient_id:
            error = "Некорректный patient_id"
        elif not encounter_type:
            error = "Заполните type"
        elif not start_dt or not end_dt:
            error = "Некорректные даты"
        elif start_dt > end_dt:
            error = "start_datetime должен быть <= end_datetime"
        else:
            patient_exists = db.query(SELECTS["PATIENT_EXISTS"], [patient_id])
            if not patient_exists:
                error = "Пациент не найден"
            elif bed_id_raw and not db.query(SELECTS["BED_EXISTS"], [bed_id]):
                error = "Койка не найдена"
            else:
                db.execute(
                    "UPDATE encounters SET patient_id=%s, bed_id=%s, type=%s, start_datetime=%s, end_datetime=%s WHERE id=%s AND doctor_id=%s",
                    [patient_id, bed_id, encounter_type, start_dt, end_dt, encounter_id, session["doctor_id"]],
                )
                success = "Прием обновлен"
                own = db.query(SELECTS["DOCTOR_OWN_ENCOUNTER_BY_ID"], [encounter_id, session["doctor_id"]])
                row = own[0]
    return render_template("doctor_edit_encounter.html", encounter=row, error=error, success=success)


@app.route("/doctor/my_patients")
def doctor_my_patients():
    if not require_doctor():
        abort(403)
    name_q = request.args.get("name", "").strip()
    patient_id_raw = request.args.get("patient_id", "").strip()
    patient_id = None
    if patient_id_raw:
        try:
            patient_id = int(patient_id_raw)
        except ValueError:
            patient_id = None
    rows = db.query(
        SELECTS["DOCTOR_PATIENTS_SEARCH"],
        [
            session["doctor_id"],
            patient_id,
            patient_id,
            name_q,
            f"%{name_q}%",
        ],
    )
    return render_template("doctor_my_patients.html", patients=rows, name=name_q, patient_id=patient_id_raw)


@app.route("/doctor/add_treatment/<int:encounter_id>", methods=["GET", "POST"])
def doctor_add_treatment(encounter_id):
    if not require_doctor():
        abort(403)
    own = db.query(SELECTS["DOCTOR_OWNS_ENCOUNTER"], [encounter_id, session["doctor_id"]])
    if not own:
        abort(404)
    error = ""
    success = ""
    if request.method == "POST":
        procedure_id_raw = request.form.get("procedure_id", "").strip()
        medication_id_raw = request.form.get("medication_id", "").strip()
        start_date = request.form.get("start_date", "").strip()
        end_date = request.form.get("end_date", "").strip()
        frequency = request.form.get("frequency", "").strip()
        item_type = request.form.get("type", "").strip()
        note = request.form.get("note", "").strip()
        procedure_id = None
        medication_id = None
        if procedure_id_raw:
            try:
                procedure_id = int(procedure_id_raw)
            except ValueError:
                procedure_id = None
        if medication_id_raw:
            try:
                medication_id = int(medication_id_raw)
            except ValueError:
                medication_id = None
        xor_ok = (procedure_id is None) != (medication_id is None)
        if not xor_ok:
            error = "Укажите ровно одно значение: procedure_id или medication_id"
        elif not start_date or not end_date:
            error = "Заполните даты"
        elif start_date > end_date:
            error = "start_date должен быть <= end_date"
        elif not frequency or not item_type or not note:
            error = "Заполните frequency, type и note"
        elif procedure_id is not None and not db.query(SELECTS["PROCEDURE_EXISTS"], [procedure_id]):
            error = "Процедура не найдена"
        elif medication_id is not None and not db.query(SELECTS["MEDICATION_EXISTS"], [medication_id]):
            error = "Препарат не найден"
        else:
            new_id = next_treatment_id()
            db.execute(
                "INSERT INTO treatment_items(id, encounter_id, procedure_id, medication_id, start_date, end_date, frequency, type, note) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                [new_id, encounter_id, procedure_id, medication_id, start_date, end_date, frequency, item_type, note],
            )
            success = f"Назначение создано, id={new_id}"
    return render_template("doctor_add_treatment.html", encounter_id=encounter_id, error=error, success=success)


@app.route("/doctor/patient/<int:patient_id>")
def doctor_patient(patient_id):
    if not require_doctor():
        abort(403)
    can_view = db.query(SELECTS["DOCTOR_CAN_VIEW_PATIENT"], [session["doctor_id"], patient_id])
    if not can_view:
        abort(403)
    patient_rows = db.query(SELECTS["PATIENT_BY_ID"], [patient_id])
    if not patient_rows:
        abort(404)
    encounters = db.query(SELECTS["DOCTOR_PATIENT_ENCOUNTERS"], [session["doctor_id"], patient_id])
    treatments = db.query(SELECTS["DOCTOR_PATIENT_TREATMENTS"], [session["doctor_id"], patient_id])
    return render_template("doctor_patient.html", patient=patient_rows[0], encounters=encounters, treatments=treatments)


@app.route("/patient/encounters")
def patient_encounters():
    if not require_patient():
        abort(403)
    rows = db.query(SELECTS["PATIENT_ENCOUNTERS"], [session["patient_id"]])
    return render_template("patient_encounters.html", encounters=rows)


@app.route("/patient/treatments")
def patient_treatments():
    if not require_patient():
        abort(403)
    rows = db.query(SELECTS["PATIENT_TREATMENTS"], [session["patient_id"]])
    return render_template("patient_treatments.html", treatments=rows)


init_db()
SELECTS = load_selects(SQL_DIR / "02_selects.sql")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("APP_PORT", "5050")))
