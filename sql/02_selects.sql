SELECT 'AUTH_DOCTOR_EXISTS';
SELECT id FROM doctors WHERE id = %s;

SELECT 'AUTH_PATIENT_EXISTS';
SELECT id FROM patients WHERE id = %s;

SELECT 'PATIENT_EXISTS';
SELECT id FROM patients WHERE id = %s;

SELECT 'BED_EXISTS';
SELECT id FROM beds WHERE id = %s;

SELECT 'NEXT_ENCOUNTER_ID';
SELECT COALESCE(MAX(id), 0) + 1 AS id FROM encounters;

SELECT 'NEXT_TREATMENT_ID';
SELECT COALESCE(MAX(id), 0) + 1 AS id FROM treatment_items;

SELECT 'DOCTOR_OWN_ENCOUNTER_BY_ID';
SELECT id, patient_id, doctor_id, bed_id, type, start_datetime, end_datetime
FROM encounters
WHERE id = %s AND doctor_id = %s;

SELECT 'DOCTOR_OWNS_ENCOUNTER';
SELECT id, patient_id, doctor_id
FROM encounters
WHERE id = %s AND doctor_id = %s;

SELECT 'PROCEDURE_EXISTS';
SELECT id FROM procedures WHERE id = %s;

SELECT 'MEDICATION_EXISTS';
SELECT id FROM medication WHERE id = %s;

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

SELECT 'DOCTOR_PATIENT_ENCOUNTERS';
SELECT e.id, e.patient_id, e.doctor_id, e.bed_id, e.type, e.start_datetime, e.end_datetime
FROM encounters e
WHERE e.doctor_id = %s AND e.patient_id = %s
ORDER BY e.start_datetime DESC;

SELECT 'DOCTOR_PATIENT_TREATMENTS';
SELECT ti.id, ti.encounter_id, ti.procedure_id, ti.medication_id, ti.start_date, ti.end_date, ti.frequency, ti.type, ti.note,
       p.name AS procedure_name, m.name AS medication_name
FROM treatment_items ti
JOIN encounters e ON e.id = ti.encounter_id
LEFT JOIN procedures p ON p.id = ti.procedure_id
LEFT JOIN medication m ON m.id = ti.medication_id
WHERE e.doctor_id = %s AND e.patient_id = %s
ORDER BY ti.start_date DESC, ti.id DESC;

SELECT 'PATIENT_ENCOUNTERS';
SELECT id, patient_id, doctor_id, bed_id, type, start_datetime, end_datetime
FROM encounters
WHERE patient_id = %s
ORDER BY start_datetime DESC;

SELECT 'PATIENT_TREATMENTS';
SELECT ti.id, ti.encounter_id, ti.procedure_id, ti.medication_id, ti.start_date, ti.end_date, ti.frequency, ti.type, ti.note,
       p.name AS procedure_name, m.name AS medication_name
FROM treatment_items ti
JOIN encounters e ON e.id = ti.encounter_id
LEFT JOIN procedures p ON p.id = ti.procedure_id
LEFT JOIN medication m ON m.id = ti.medication_id
WHERE e.patient_id = %s
ORDER BY ti.start_date DESC, ti.id DESC;
