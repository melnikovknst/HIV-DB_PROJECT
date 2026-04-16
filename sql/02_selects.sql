SELECT 'AUTH_DOCTOR_EXISTS';
SELECT id FROM doctors WHERE id = %s;

SELECT 'AUTH_PATIENT_EXISTS';
SELECT id FROM patients WHERE id = %s;

SELECT 'PATIENT_EXISTS';
SELECT id FROM patients WHERE id = %s;

SELECT 'BED_EXISTS';
SELECT id FROM beds WHERE id = %s;

SELECT 'BED_IS_FREE';
SELECT id FROM beds WHERE id = %s AND LOWER(status) IN ('free', 'available');

SELECT 'NEXT_ENCOUNTER_ID';
SELECT COALESCE(MAX(id), 0) + 1 AS id FROM encounters;

SELECT 'NEXT_DIAGNOSIS_ID';
SELECT COALESCE(MAX(id), 0) + 1 AS id FROM diagnoses;

SELECT 'NEXT_TREATMENT_ID';
SELECT COALESCE(MAX(id), 0) + 1 AS id FROM treatment_items;

SELECT 'DOCTOR_ENCOUNTER_BY_ID';
SELECT e.id, e.patient_id, e.doctor_id, e.bed_id, e.type, e.start_datetime, e.end_datetime,
       p.name AS patient_name
FROM encounters e
JOIN patients p ON p.id = e.patient_id
WHERE e.id = %s AND e.doctor_id = %s;

SELECT 'DOCTOR_OWN_ENCOUNTER_BY_ID';
SELECT id, patient_id, doctor_id, bed_id, type, start_datetime, end_datetime
FROM encounters
WHERE id = %s AND doctor_id = %s;

SELECT 'DOCTOR_OWNS_ENCOUNTER';
SELECT id, patient_id, doctor_id
FROM encounters
WHERE id = %s AND doctor_id = %s;

SELECT 'PATIENT_BY_ENCOUNTER_FOR_DOCTOR';
SELECT p.id, p.name, p.sex, p.phone, p.email, p.snus, p.passport, p.birth_date,
       e.id AS encounter_id, e.doctor_id
FROM encounters e
JOIN patients p ON p.id = e.patient_id
WHERE e.id = %s AND e.doctor_id = %s;

SELECT 'PROCEDURE_EXISTS';
SELECT id FROM procedures WHERE id = %s;

SELECT 'MEDICATION_EXISTS';
SELECT id FROM medication WHERE id = %s;

SELECT 'PROCEDURES_LIST';
SELECT id, code, name, default_duration_min
FROM procedures
ORDER BY name;

SELECT 'MEDICATIONS_LIST';
SELECT id, name, form, strength
FROM medication
ORDER BY name;

SELECT 'BEDS_LIST';
SELECT b.id, b.status, b.department_id, d.name AS department_name
FROM beds b
JOIN departments d ON d.id = b.department_id
ORDER BY CASE WHEN b.status = 'free' THEN 0 ELSE 1 END, d.name, b.id;

SELECT 'BEDS_FREE_LIST';
SELECT b.id, b.status, b.department_id, d.name AS department_name
FROM beds b
JOIN departments d ON d.id = b.department_id
WHERE LOWER(b.status) IN ('free', 'available')
ORDER BY d.name, b.id;

SELECT 'DOCTOR_PATIENTS_SEARCH';
SELECT p.id, p.name, p.sex, p.phone, p.email, p.snus, p.passport, p.birth_date
FROM get_doctor_patients(%s) p
WHERE (%s IS NULL OR p.id = %s)
AND (%s = '' OR LOWER(p.name) LIKE LOWER(%s))
ORDER BY p.name;

SELECT 'DOCTOR_CAN_VIEW_PATIENT';
SELECT 1
FROM encounters
WHERE doctor_id = %s AND patient_id = %s
LIMIT 1;

SELECT 'PATIENT_BY_ID';
SELECT id, name, sex, phone, email, snus, passport, birth_date
FROM patients
WHERE id = %s;

SELECT 'PATIENTS_LIST';
SELECT id, name, sex, phone, email, snus, passport, birth_date
FROM patients
ORDER BY name;

SELECT 'DOCTOR_PATIENTS_SEARCH_BY_FIELD';
SELECT p.id, p.name, p.sex, p.phone, p.email, p.snus, p.passport, p.birth_date
FROM get_doctor_patients(%s) p
WHERE (
  (%s = 'name' AND (%s = '' OR LOWER(p.name) LIKE LOWER(%s)))
  OR (%s = 'phone' AND (%s = '' OR p.phone LIKE %s))
  OR (%s = 'snus' AND (%s = '' OR p.snus LIKE %s))
  OR (%s = 'passport' AND (%s = '' OR REPLACE(p.passport, ' ', '') LIKE %s))
  OR (%s = 'email' AND (%s = '' OR LOWER(p.email) LIKE LOWER(%s)))
  OR (%s = 'sex' AND (%s = '' OR p.sex = %s))
  OR (%s = 'birth_date' AND (%s IS NULL OR p.birth_date >= %s) AND (%s IS NULL OR p.birth_date <= %s))
)
ORDER BY p.name;

SELECT 'DOCTOR_PATIENT_ENCOUNTERS';
SELECT e.id, e.patient_id, e.doctor_id, e.bed_id, e.type, e.start_datetime, e.end_datetime,
       b.status AS bed_status, d.name AS department_name
FROM encounters e
LEFT JOIN beds b ON b.id = e.bed_id
LEFT JOIN departments d ON d.id = b.department_id
WHERE e.doctor_id = %s AND e.patient_id = %s
ORDER BY e.start_datetime DESC, e.id DESC;

SELECT 'DOCTOR_PATIENT_DIAGNOSES';
SELECT dg.id, dg.patient_id, dg.encounter_id, dg.icd10_code, dg.diagnosis_type, dg.diagnosed_at, dg.notes,
       e.type AS encounter_type, e.start_datetime AS encounter_start
FROM diagnoses dg
JOIN encounters e ON e.id = dg.encounter_id
WHERE e.doctor_id = %s AND e.patient_id = %s
ORDER BY dg.diagnosed_at DESC, dg.id DESC;

SELECT 'DOCTOR_PATIENT_TREATMENTS';
SELECT ti.id, ti.encounter_id, ti.procedure_id, ti.medication_id, ti.start_date, ti.end_date, ti.frequency, ti.type, ti.note,
       p.name AS procedure_name, m.name AS medication_name, m.form AS medication_form, m.strength AS medication_strength
FROM treatment_items ti
JOIN encounters e ON e.id = ti.encounter_id
LEFT JOIN procedures p ON p.id = ti.procedure_id
LEFT JOIN medication m ON m.id = ti.medication_id
WHERE e.doctor_id = %s AND e.patient_id = %s
ORDER BY ti.start_date DESC, ti.id DESC;

SELECT 'PATIENT_ENCOUNTERS';
SELECT e.id, e.patient_id, e.doctor_id, e.bed_id, e.type, e.start_datetime, e.end_datetime, s.name AS doctor_name
FROM encounters e
JOIN staff s ON s.id = e.doctor_id
WHERE e.patient_id = %s
ORDER BY e.start_datetime DESC;

SELECT 'PATIENT_ENCOUNTERS_SEARCH';
SELECT e.id, e.patient_id, e.doctor_id, e.bed_id, e.type, e.start_datetime, e.end_datetime, s.name AS doctor_name
FROM encounters e
JOIN staff s ON s.id = e.doctor_id
WHERE e.patient_id = %s
AND (%s <> 'doctor' OR %s = '' OR LOWER(s.name) LIKE LOWER(%s))
AND (%s <> 'type' OR %s = '' OR e.type = %s)
AND (
  %s <> 'date_start'
  OR (
    (%s IS NULL OR e.start_datetime::date >= %s)
    AND (%s IS NULL OR e.start_datetime::date <= %s)
  )
)
ORDER BY e.start_datetime DESC;

SELECT 'PATIENT_TREATMENTS';
SELECT ti.id, ti.encounter_id, ti.procedure_id, ti.medication_id, ti.start_date, ti.end_date, ti.frequency, ti.type, ti.note,
       p.name AS procedure_name, m.name AS medication_name, s.name AS doctor_name, e.type AS encounter_type
FROM treatment_items ti
JOIN encounters e ON e.id = ti.encounter_id
JOIN staff s ON s.id = e.doctor_id
LEFT JOIN procedures p ON p.id = ti.procedure_id
LEFT JOIN medication m ON m.id = ti.medication_id
WHERE e.patient_id = %s
ORDER BY ti.start_date DESC, ti.id DESC;
