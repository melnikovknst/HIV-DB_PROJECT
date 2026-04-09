from datetime import date, datetime, timedelta
import random
import db


TARGET_STAFF = 300
TARGET_DOCTORS = 96
TARGET_BEDS = 300
TARGET_PATIENTS = 300
TARGET_ENCOUNTERS = 360
TARGET_DIAGNOSES = 360
TARGET_TREATMENTS = 360


INSTITUTIONS = [
    (1, "Городская клиническая больница №1", "hospital", "+7-383-210-10-01", "gkb1@meddemo.ru"),
    (2, "Городская поликлиника №4", "polyclinic", "+7-383-210-10-02", "gp4@meddemo.ru"),
    (3, "Областная клиническая больница", "regional_hospital", "+7-383-210-10-03", "okb@meddemo.ru"),
    (4, "Диагностический центр Сибирь", "diagnostic_center", "+7-383-210-10-04", "dc@meddemo.ru"),
    (5, "Медицинский центр Здоровье Плюс", "private_center", "+7-383-210-10-05", "info@zdorovieplus.ru"),
    (6, "Городская детская больница №2", "children_hospital", "+7-383-210-10-06", "gdb2@meddemo.ru"),
    (7, "Инфекционная клиническая больница", "infectious_hospital", "+7-383-210-10-07", "ikb@meddemo.ru"),
    (8, "Кардиологический диспансер", "dispensary", "+7-383-210-10-08", "cardio@meddemo.ru"),
    (9, "Центр амбулаторной хирургии", "surgery_center", "+7-383-210-10-09", "surg@meddemo.ru"),
    (10, "Перинатальный центр", "perinatal_center", "+7-383-210-10-10", "perinatal@meddemo.ru"),
    (11, "Реабилитационный центр Надежда", "rehab_center", "+7-383-210-10-11", "rehab@meddemo.ru"),
    (12, "Северная районная больница", "district_hospital", "+7-383-210-10-12", "north@meddemo.ru"),
]


DEPARTMENTS = [
    (1, "Приемное отделение", "+7-383-310-20-01", "admission", 1),
    (2, "Терапевтическое отделение", "+7-383-310-20-02", "inpatient", 1),
    (3, "Кардиологическое отделение", "+7-383-310-20-03", "inpatient", 1),
    (4, "Неврологическое отделение", "+7-383-310-20-04", "inpatient", 1),
    (5, "Хирургическое отделение", "+7-383-310-20-05", "inpatient", 3),
    (6, "Инфекционное отделение", "+7-383-310-20-06", "inpatient", 7),
    (7, "Дневной стационар", "+7-383-310-20-07", "day_hospital", 2),
    (8, "Диагностическое отделение", "+7-383-310-20-08", "diagnostic", 4),
    (9, "Поликлиническое отделение", "+7-383-310-20-09", "outpatient", 2),
    (10, "Эндокринологическое отделение", "+7-383-310-20-10", "inpatient", 3),
    (11, "Педиатрическое отделение", "+7-383-310-20-11", "inpatient", 6),
    (12, "Травматологическое отделение", "+7-383-310-20-12", "inpatient", 3),
    (13, "Оториноларингологическое отделение", "+7-383-310-20-13", "outpatient", 2),
    (14, "Дерматовенерологическое отделение", "+7-383-310-20-14", "outpatient", 5),
    (15, "Офтальмологическое отделение", "+7-383-310-20-15", "outpatient", 5),
    (16, "Гастроэнтерологическое отделение", "+7-383-310-20-16", "inpatient", 12),
    (17, "Урологическое отделение", "+7-383-310-20-17", "inpatient", 12),
    (18, "Гинекологическое отделение", "+7-383-310-20-18", "inpatient", 10),
    (19, "Реанимация", "+7-383-310-20-19", "icu", 3),
    (20, "Анестезиология", "+7-383-310-20-20", "surgery_support", 3),
    (21, "Кабинет инфекциониста", "+7-383-310-20-21", "outpatient", 7),
    (22, "Кабинет кардиолога", "+7-383-310-20-22", "outpatient", 8),
    (23, "Кабинет невролога", "+7-383-310-20-23", "outpatient", 2),
    (24, "Амбулаторная хирургия", "+7-383-310-20-24", "outpatient", 9),
    (25, "Физиотерапевтическое отделение", "+7-383-310-20-25", "rehab", 11),
    (26, "Реабилитационное отделение", "+7-383-310-20-26", "rehab", 11),
    (27, "Клиническая лаборатория", "+7-383-310-20-27", "diagnostic", 4),
    (28, "Лучевая диагностика", "+7-383-310-20-28", "diagnostic", 4),
    (29, "Кабинет эндокринолога", "+7-383-310-20-29", "outpatient", 2),
    (30, "Кабинет терапевта", "+7-383-310-20-30", "outpatient", 2),
]


SPECIALIZATIONS = [
    (1, "THER", "Терапевт"),
    (2, "CARD", "Кардиолог"),
    (3, "NEUR", "Невролог"),
    (4, "SURG", "Хирург"),
    (5, "ENDO", "Эндокринолог"),
    (6, "PED", "Педиатр"),
    (7, "TRAU", "Травматолог"),
    (8, "ENT", "ЛОР"),
    (9, "DERM", "Дерматолог"),
    (10, "OPHT", "Офтальмолог"),
    (11, "GAST", "Гастроэнтеролог"),
    (12, "UROL", "Уролог"),
    (13, "GYNE", "Гинеколог"),
    (14, "INFD", "Инфекционист"),
    (15, "ANES", "Анестезиолог"),
    (16, "REAN", "Реаниматолог"),
]


PROCEDURES = [
    (1, "PROC-CBC", "Общий анализ крови", 15),
    (2, "PROC-BIO", "Биохимический анализ крови", 20),
    (3, "PROC-ECG", "ЭКГ", 20),
    (4, "PROC-ECHO", "ЭхоКГ", 30),
    (5, "PROC-MRI", "МРТ головного мозга", 50),
    (6, "PROC-XRAY", "Рентгенография грудной клетки", 25),
    (7, "PROC-US", "УЗИ брюшной полости", 30),
    (8, "PROC-IV", "Капельница", 60),
    (9, "PROC-DRESS", "Перевязка", 20),
    (10, "PROC-INH", "Ингаляция", 20),
    (11, "PROC-PHYS", "Физиотерапия", 40),
    (12, "PROC-MASS", "Массаж", 40),
    (13, "PROC-INJ", "Внутривенное введение препарата", 25),
    (14, "PROC-EEG", "ЭЭГ", 35),
    (15, "PROC-ENDO", "Эндоскопия", 45),
    (16, "PROC-CT", "КТ органов грудной клетки", 35),
    (17, "PROC-WASH", "Промывание носа", 15),
    (18, "PROC-CONS", "Повторная консультация специалиста", 25),
]


MEDICATIONS = [
    (1, "Парацетамол", "таблетки", "500 мг"),
    (2, "Ибупрофен", "таблетки", "200 мг"),
    (3, "Амоксициллин", "капсулы", "500 мг"),
    (4, "Азитромицин", "таблетки", "500 мг"),
    (5, "Омепразол", "капсулы", "20 мг"),
    (6, "Лозартан", "таблетки", "50 мг"),
    (7, "Метформин", "таблетки", "850 мг"),
    (8, "Но-шпа", "таблетки", "40 мг"),
    (9, "Цефтриаксон", "порошок для инъекций", "1 г"),
    (10, "Аторвастатин", "таблетки", "20 мг"),
    (11, "Амброксол", "сироп", "15 мг/5 мл"),
    (12, "Сальбутамол", "аэрозоль", "100 мкг"),
    (13, "Эналаприл", "таблетки", "10 мг"),
    (14, "Инсулин гларгин", "раствор", "100 ЕД/мл"),
    (15, "Магния сульфат", "раствор", "25%"),
    (16, "Диклофенак", "таблетки", "50 мг"),
    (17, "Пантопразол", "таблетки", "40 мг"),
    (18, "Левофлоксацин", "таблетки", "500 мг"),
]


ICD_CODES = [
    ("I10", "Артериальная гипертензия"),
    ("J06.9", "Острая инфекция верхних дыхательных путей"),
    ("E11.9", "Сахарный диабет 2 типа"),
    ("K29.7", "Гастрит"),
    ("M54.5", "Боль в пояснице"),
    ("N39.0", "Инфекция мочевыводящих путей"),
    ("G43.9", "Мигрень"),
    ("J18.9", "Пневмония"),
    ("R51", "Головная боль"),
    ("B34.9", "Вирусная инфекция неуточненная"),
    ("H52.4", "Пресбиопия"),
    ("L20.9", "Атопический дерматит"),
    ("S93.4", "Растяжение связок голеностопа"),
    ("J45.9", "Бронхиальная астма"),
    ("K80.2", "Желчнокаменная болезнь"),
    ("N20.0", "Камни почки"),
]


DIAGNOSIS_TYPES = ["primary", "secondary", "discharge", "preliminary"]
BED_STATUSES = ["available", "occupied", "cleaning", "maintenance"]
ENCOUNTER_TYPES = ["outpatient", "inpatient", "consultation", "follow_up", "diagnostic"]
FREQUENCIES = ["one_time", "once_daily", "twice_daily", "three_times_daily", "weekly"]

MALE_FIRST = [
    "Александр", "Дмитрий", "Максим", "Иван", "Сергей", "Андрей", "Алексей", "Николай",
    "Павел", "Егор", "Михаил", "Виктор", "Роман", "Олег", "Владимир", "Константин",
]
FEMALE_FIRST = [
    "Елена", "Ольга", "Наталья", "Анна", "Мария", "Светлана", "Татьяна", "Ирина",
    "Екатерина", "Юлия", "Виктория", "Ксения", "Дарья", "Людмила", "Алена", "Полина",
]
MALE_LAST = [
    "Иванов", "Петров", "Сидоров", "Кузнецов", "Смирнов", "Васильев", "Новиков", "Федоров",
    "Морозов", "Волков", "Соловьев", "Егоров", "Павлов", "Орлов", "Никитин", "Тихонов",
]
FEMALE_LAST = [
    "Иванова", "Петрова", "Сидорова", "Кузнецова", "Смирнова", "Васильева", "Новикова", "Федорова",
    "Морозова", "Волкова", "Соловьева", "Егорова", "Павлова", "Орлова", "Никитина", "Тихонова",
]
MALE_MIDDLE = [
    "Александрович", "Дмитриевич", "Иванович", "Сергеевич", "Андреевич", "Павлович", "Николаевич", "Викторович",
]
FEMALE_MIDDLE = [
    "Александровна", "Дмитриевна", "Ивановна", "Сергеевна", "Андреевна", "Павловна", "Николаевна", "Викторовна",
]


def query_value(sql_text):
    rows = db.query(sql_text)
    return rows[0]["value"]


def count_rows(table_name):
    return int(query_value(f"SELECT COUNT(*) AS value FROM {table_name}"))


def max_id(table_name):
    return int(query_value(f"SELECT COALESCE(MAX(id), 0) AS value FROM {table_name}"))


def upsert_reference_data():
    db.execute_many(
        "INSERT INTO medical_institutions(id, name, type, phone, email) VALUES (%s, %s, %s, %s, %s) "
        "ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, type = EXCLUDED.type, phone = EXCLUDED.phone, email = EXCLUDED.email",
        INSTITUTIONS,
    )
    db.execute_many(
        "INSERT INTO departments(id, name, phone, type, institution_id) VALUES (%s, %s, %s, %s, %s) "
        "ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, phone = EXCLUDED.phone, type = EXCLUDED.type, institution_id = EXCLUDED.institution_id",
        DEPARTMENTS,
    )
    db.execute_many(
        "INSERT INTO specializations(id, code, name) VALUES (%s, %s, %s) "
        "ON CONFLICT (id) DO UPDATE SET code = EXCLUDED.code, name = EXCLUDED.name",
        SPECIALIZATIONS,
    )
    db.execute_many(
        "INSERT INTO procedures(id, code, name, default_duration_min) VALUES (%s, %s, %s, %s) "
        "ON CONFLICT (id) DO UPDATE SET code = EXCLUDED.code, name = EXCLUDED.name, default_duration_min = EXCLUDED.default_duration_min",
        PROCEDURES,
    )
    db.execute_many(
        "INSERT INTO medication(id, name, form, strength) VALUES (%s, %s, %s, %s) "
        "ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, form = EXCLUDED.form, strength = EXCLUDED.strength",
        MEDICATIONS,
    )


def make_name(rng, female):
    first = rng.choice(FEMALE_FIRST if female else MALE_FIRST)
    last = rng.choice(FEMALE_LAST if female else MALE_LAST)
    middle = rng.choice(FEMALE_MIDDLE if female else MALE_MIDDLE)
    return f"{last} {first} {middle}"


def make_phone(prefix, number):
    area = 900 + (number % 90)
    part1 = 100 + ((number * 7) % 900)
    part2 = 10 + ((number * 11) % 90)
    part3 = 10 + ((number * 13) % 90)
    return f"+7-{area}-{part1}-{part2}-{part3}"


def make_snils(number):
    return f"{100 + number % 900:03d}-{100 + (number * 3) % 900:03d}-{100 + (number * 7) % 900:03d} {10 + number % 90:02d}"


def make_passport(series, number):
    return f"{series:04d} {number:06d}"


def generate_staff():
    staff_count = count_rows("staff")
    doctors_count = count_rows("doctors")
    if staff_count >= TARGET_STAFF and doctors_count >= TARGET_DOCTORS:
        return
    rng = random.Random(42017)
    department_ids = [row["id"] for row in db.query("SELECT id FROM departments ORDER BY id")]
    needed_staff = max(0, TARGET_STAFF - staff_count)
    needed_doctors = max(0, TARGET_DOCTORS - doctors_count)
    start_id = max_id("staff") + 1
    staff_rows = []
    doctor_rows = []
    start_date = date(2005, 1, 10)
    for offset in range(needed_staff):
        current_id = start_id + offset
        female = current_id % 3 != 0
        staff_type = "doctor" if offset < needed_doctors else ["nurse", "administrator", "lab_assistant", "paramedic"][offset % 4]
        department_id = department_ids[offset % len(department_ids)]
        hire_date = start_date + timedelta(days=(offset * 29) % 5600)
        staff_rows.append(
            (
                current_id,
                department_id,
                make_name(rng, female),
                make_phone("staff", current_id),
                f"staff{current_id}@meddemo.ru",
                hire_date,
                staff_type,
                True,
                f"5401{current_id:08d}"[-12:],
            )
        )
        if staff_type == "doctor":
            doctor_rows.append((current_id, 2 + (offset % 34)))
    if staff_rows:
        db.execute_many(
            "INSERT INTO staff(id, department_id, name, phone, email, hire_date, staff_type, is_active, inn) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            staff_rows,
        )
    if doctor_rows:
        db.execute_many(
            "INSERT INTO doctors(id, experience_years) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
            doctor_rows,
        )


def generate_doctor_specializations():
    rng = random.Random(55123)
    doctors = [row["id"] for row in db.query("SELECT id FROM doctors ORDER BY id")]
    pairs = []
    for doctor_id in doctors:
        primary = (doctor_id % len(SPECIALIZATIONS)) + 1
        secondary = ((doctor_id * 3) % len(SPECIALIZATIONS)) + 1
        pairs.append((doctor_id, primary))
        if secondary != primary:
            pairs.append((doctor_id, secondary))
        if doctor_id % 5 == 0:
            tertiary = rng.randint(1, len(SPECIALIZATIONS))
            if tertiary not in {primary, secondary}:
                pairs.append((doctor_id, tertiary))
    db.execute_many(
        "INSERT INTO doctors_specializations(doctor_id, specialization_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        pairs,
    )


def generate_beds():
    bed_count = count_rows("beds")
    if bed_count >= TARGET_BEDS:
        return
    eligible_departments = [row["id"] for row in db.query("SELECT id FROM departments WHERE type IN ('inpatient', 'day_hospital', 'icu', 'rehab', 'admission') ORDER BY id")]
    needed = TARGET_BEDS - bed_count
    start_id = max_id("beds") + 1
    rows = []
    for offset in range(needed):
        current_id = start_id + offset
        department_id = eligible_departments[offset % len(eligible_departments)]
        status = BED_STATUSES[(offset + current_id) % len(BED_STATUSES)]
        rows.append((current_id, status, department_id))
    db.execute_many(
        "INSERT INTO beds(id, status, department_id) VALUES (%s, %s, %s)",
        rows,
    )


def generate_patients():
    patient_count = count_rows("patients")
    if patient_count >= TARGET_PATIENTS:
        return
    rng = random.Random(99107)
    needed = TARGET_PATIENTS - patient_count
    start_id = max_id("patients") + 1
    rows = []
    start_birth = date(1948, 1, 1)
    for offset in range(needed):
        current_id = start_id + offset
        female = current_id % 2 == 0
        birth_date = start_birth + timedelta(days=(offset * 173) % 24000)
        rows.append(
            (
                current_id,
                make_name(rng, female),
                "F" if female else "M",
                make_phone("patient", current_id),
                f"patient{current_id}@maildemo.ru",
                make_snils(current_id),
                make_passport(4500 + (current_id % 20), 100000 + current_id),
                birth_date,
            )
        )
    db.execute_many(
        "INSERT INTO patients(id, name, sex, phone, email, snus, passport, birth_date) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        rows,
    )


def build_encounter_patient_sequence(patient_ids, needed):
    sequence = [1, 1, 1, 2, 3, 4, 5, 1, 6, 7, 8, 9, 10]
    index = 0
    while len(sequence) < needed:
        sequence.append(patient_ids[index % len(patient_ids)])
        if index % 4 == 0:
            sequence.append(patient_ids[(index * 7 + 3) % len(patient_ids)])
        index += 1
    return sequence[:needed]


def build_encounter_doctor_sequence(doctor_ids, needed):
    heavy = [doctor_id for doctor_id in doctor_ids[:18] for _ in range(6)]
    medium = [doctor_id for doctor_id in doctor_ids[18:42] for _ in range(3)]
    light = doctor_ids[42:]
    pool = [1] * 20 + heavy + medium + light
    sequence = []
    index = 0
    while len(sequence) < needed:
        sequence.append(pool[index % len(pool)])
        index += 5
    return sequence


def generate_encounters():
    encounter_count = count_rows("encounters")
    if encounter_count >= TARGET_ENCOUNTERS:
        return []
    patient_ids = [row["id"] for row in db.query("SELECT id FROM patients ORDER BY id")]
    doctor_ids = [row["id"] for row in db.query("SELECT id FROM doctors ORDER BY id")]
    bed_ids = [row["id"] for row in db.query("SELECT id FROM beds ORDER BY id")]
    needed = TARGET_ENCOUNTERS - encounter_count
    start_id = max_id("encounters") + 1
    patient_sequence = build_encounter_patient_sequence(patient_ids, needed)
    doctor_sequence = build_encounter_doctor_sequence(doctor_ids, needed)
    rows = []
    created = []
    base_dt = datetime(2024, 1, 10, 8, 0)
    for offset in range(needed):
        current_id = start_id + offset
        patient_id = patient_sequence[offset]
        doctor_id = doctor_sequence[offset]
        encounter_type = ENCOUNTER_TYPES[offset % len(ENCOUNTER_TYPES)]
        start_dt = base_dt + timedelta(days=offset, hours=(offset * 3) % 9)
        if encounter_type == "inpatient":
            end_dt = start_dt + timedelta(days=3 + (offset % 6), hours=4)
            bed_id = bed_ids[offset % len(bed_ids)]
        elif encounter_type == "diagnostic":
            end_dt = start_dt + timedelta(hours=2)
            bed_id = None
        elif encounter_type == "consultation":
            end_dt = start_dt + timedelta(minutes=40)
            bed_id = None
        elif encounter_type == "follow_up":
            end_dt = start_dt + timedelta(minutes=30)
            bed_id = None
        else:
            end_dt = start_dt + timedelta(minutes=50)
            bed_id = None
        row = (current_id, patient_id, doctor_id, bed_id, encounter_type, start_dt, end_dt)
        rows.append(row)
        created.append(
            {
                "id": current_id,
                "patient_id": patient_id,
                "doctor_id": doctor_id,
                "bed_id": bed_id,
                "type": encounter_type,
                "start_datetime": start_dt,
                "end_datetime": end_dt,
            }
        )
    db.execute_many(
        "INSERT INTO encounters(id, patient_id, doctor_id, bed_id, type, start_datetime, end_datetime) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        rows,
    )
    return created


def generate_diagnoses(new_encounters):
    diagnosis_count = count_rows("diagnoses")
    needed = TARGET_DIAGNOSES - diagnosis_count
    if needed <= 0:
        return
    start_id = max_id("diagnoses") + 1
    source = list(new_encounters)
    if len(source) < needed:
        missing = db.query(
            "SELECT e.id, e.patient_id, e.doctor_id, e.bed_id, e.type, e.start_datetime, e.end_datetime "
            "FROM encounters e LEFT JOIN diagnoses d ON d.encounter_id = e.id "
            "WHERE d.id IS NULL ORDER BY e.id LIMIT %s",
            [needed - len(source)],
        )
        source.extend(missing)
    source = source[:needed]
    rows = []
    for offset, encounter in enumerate(source):
        current_id = start_id + offset
        code, description = ICD_CODES[offset % len(ICD_CODES)]
        rows.append(
            (
                current_id,
                encounter["patient_id"],
                encounter["id"],
                code,
                DIAGNOSIS_TYPES[offset % len(DIAGNOSIS_TYPES)],
                encounter["start_datetime"] + timedelta(minutes=20),
                f"{description}. Контроль состояния и клиническое наблюдение.",
            )
        )
    db.execute_many(
        "INSERT INTO diagnoses(id, patient_id, encounter_id, icd10_code, diagnosis_type, diagnosed_at, notes) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        rows,
    )


def generate_treatments(new_encounters):
    treatment_count = count_rows("treatment_items")
    needed = TARGET_TREATMENTS - treatment_count
    if needed <= 0:
        return
    start_id = max_id("treatment_items") + 1
    source = list(new_encounters)
    if len(source) < needed:
        missing = db.query(
            "SELECT e.id, e.patient_id, e.doctor_id, e.bed_id, e.type, e.start_datetime, e.end_datetime "
            "FROM encounters e LEFT JOIN treatment_items t ON t.encounter_id = e.id "
            "WHERE t.id IS NULL ORDER BY e.id LIMIT %s",
            [needed - len(source)],
        )
        source.extend(missing)
    source = source[:needed]
    rows = []
    for offset, encounter in enumerate(source):
        current_id = start_id + offset
        start_date = encounter["start_datetime"].date()
        end_date = encounter["end_datetime"].date()
        if offset % 2 == 0:
            procedure_id = (offset % len(PROCEDURES)) + 1
            medication_id = None
            item_type = "procedure"
            note = f"Назначена процедура: {PROCEDURES[(offset % len(PROCEDURES))][2].lower()}."
        else:
            procedure_id = None
            medication_id = (offset % len(MEDICATIONS)) + 1
            item_type = "medication"
            note = f"Медикаментозная терапия: {MEDICATIONS[(offset % len(MEDICATIONS))][1].lower()}."
        rows.append(
            (
                current_id,
                encounter["id"],
                procedure_id,
                medication_id,
                start_date,
                end_date if end_date >= start_date else start_date,
                FREQUENCIES[offset % len(FREQUENCIES)],
                item_type,
                note,
            )
        )
    db.execute_many(
        "INSERT INTO treatment_items(id, encounter_id, procedure_id, medication_id, start_date, end_date, frequency, type, note) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        rows,
    )


def ensure_demo_data():
    upsert_reference_data()
    generate_staff()
    generate_doctor_specializations()
    generate_beds()
    generate_patients()
    new_encounters = generate_encounters()
    generate_diagnoses(new_encounters)
    generate_treatments(new_encounters)
