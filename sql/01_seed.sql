INSERT INTO medical_institutions(id, name, type, phone, email) VALUES
(1, 'Novosibirsk City Clinical Hospital 1', 'Hospital', '+7-383-201-10-01', 'info@gkb1nsk.ru'),
(2, 'Regional Infectious Disease Center', 'Center', '+7-383-201-10-02', 'contact@infectcenter54.ru'),
(3, 'Central Polyclinic No 5', 'Polyclinic', '+7-383-201-10-03', 'registry@cp5nsk.ru'),
(4, 'Ob River Medical Campus', 'Hospital', '+7-383-201-10-04', 'office@obmedcampus.ru'),
(5, 'Siberian Preventive Clinic', 'Clinic', '+7-383-201-10-05', 'hello@spclinic.ru');

INSERT INTO departments(id, name, phone, type, institution_id) VALUES
(1, 'Infectious Diseases Ward A', '+7-383-301-20-01', 'Inpatient', 1),
(2, 'Outpatient HIV Care', '+7-383-301-20-02', 'Outpatient', 2),
(3, 'Internal Medicine', '+7-383-301-20-03', 'Inpatient', 4),
(4, 'Diagnostics Unit', '+7-383-301-20-04', 'Diagnostic', 3),
(5, 'Day Hospital', '+7-383-301-20-05', 'DayCare', 5),
(6, 'Emergency Intake', '+7-383-301-20-06', 'Emergency', 1);

INSERT INTO beds(id, status, department_id) VALUES
(1, 'free', 1),
(2, 'occupied', 1),
(3, 'free', 3),
(4, 'sanitation', 3),
(5, 'occupied', 5),
(6, 'free', 5);

INSERT INTO staff(id, department_id, name, phone, email, hire_date, staff_type, is_active, inn) VALUES
(1, 1, 'Ivan Petrov', '+7-913-111-00-01', 'i.petrov@hosp.ru', '2012-03-12', 'doctor', true, '540100000001'),
(2, 2, 'Elena Sidorova', '+7-913-111-00-02', 'e.sidorova@hosp.ru', '2015-06-20', 'doctor', true, '540100000002'),
(3, 3, 'Mikhail Orlov', '+7-913-111-00-03', 'm.orlov@hosp.ru', '2010-11-02', 'doctor', true, '540100000003'),
(4, 5, 'Olga Romanova', '+7-913-111-00-04', 'o.romanova@hosp.ru', '2018-01-15', 'doctor', true, '540100000004'),
(5, 6, 'Dmitry Smirnov', '+7-913-111-00-05', 'd.smirnov@hosp.ru', '2014-09-01', 'doctor', true, '540100000005'),
(6, 1, 'Anna Kuznetsova', '+7-913-111-00-06', 'a.kuznetsova@hosp.ru', '2019-04-22', 'nurse', true, '540100000006');

INSERT INTO doctors(id, experience_years) VALUES
(1, 14),
(2, 11),
(3, 16),
(4, 8),
(5, 12);

INSERT INTO specializations(id, code, name) VALUES
(1, 'INF', 'Infectious Diseases'),
(2, 'THR', 'Therapy'),
(3, 'IMM', 'Immunology'),
(4, 'EMR', 'Emergency Medicine'),
(5, 'CAR', 'Cardiology'),
(6, 'DER', 'Dermatology');

INSERT INTO doctors_specializations(doctor_id, specialization_id) VALUES
(1, 1),
(1, 3),
(2, 1),
(3, 2),
(4, 5),
(5, 4);

INSERT INTO patients(id, name, sex, phone, email, snus, passport, birth_date) VALUES
(1, 'Sergey Ivanov', 'M', '+7-923-500-10-01', 'sergey.ivanov@mail.ru', '123-456-789 01', '5001 123456', '1987-05-14'),
(2, 'Natalia Fedorova', 'F', '+7-923-500-10-02', 'n.fedorova@mail.ru', '123-456-789 02', '5002 223344', '1991-09-03'),
(3, 'Pavel Mironov', 'M', '+7-923-500-10-03', 'p.mironov@mail.ru', '123-456-789 03', '5003 332211', '1979-12-22'),
(4, 'Irina Lebedeva', 'F', '+7-923-500-10-04', 'i.lebedeva@mail.ru', '123-456-789 04', '5004 445566', '1985-07-08'),
(5, 'Andrey Volkov', 'M', '+7-923-500-10-05', 'a.volkov@mail.ru', '123-456-789 05', '5005 778899', '1994-02-17'),
(6, 'Marina Egorova', 'F', '+7-923-500-10-06', 'm.egorova@mail.ru', '123-456-789 06', '5006 990011', '1989-10-29');

INSERT INTO encounters(id, patient_id, doctor_id, bed_id, type, start_datetime, end_datetime) VALUES
(1, 1, 1, 2, 'inpatient', '2026-03-01 09:00:00', '2026-03-05 12:00:00'),
(2, 2, 1, NULL, 'outpatient', '2026-03-06 10:30:00', '2026-03-06 11:00:00'),
(3, 3, 2, NULL, 'consultation', '2026-03-07 14:00:00', '2026-03-07 14:40:00'),
(4, 4, 3, 5, 'day_hospital', '2026-03-10 08:30:00', '2026-03-10 16:30:00'),
(5, 5, 4, NULL, 'consultation', '2026-03-12 13:00:00', '2026-03-12 13:25:00'),
(6, 6, 5, 3, 'inpatient', '2026-03-15 11:00:00', '2026-03-18 10:00:00');

INSERT INTO diagnoses(id, patient_id, encounter_id, icd10_code, diagnosis_type, diagnosed_at, notes) VALUES
(1, 1, 1, 'B20', 'primary', '2026-03-01 10:00:00', 'HIV disease with infectious manifestations'),
(2, 2, 2, 'Z21', 'followup', '2026-03-06 10:45:00', 'Asymptomatic HIV status monitoring'),
(3, 3, 3, 'B24', 'primary', '2026-03-07 14:20:00', 'Unspecified HIV disease'),
(4, 4, 4, 'R50', 'secondary', '2026-03-10 09:15:00', 'Fever observation and evaluation'),
(5, 5, 5, 'I10', 'secondary', '2026-03-12 13:15:00', 'Essential hypertension'),
(6, 6, 6, 'J18', 'secondary', '2026-03-15 13:00:00', 'Pneumonia management');

INSERT INTO medication(id, name, form, strength) VALUES
(1, 'Dolutegravir', 'tablet', '50 mg'),
(2, 'Lamivudine', 'tablet', '300 mg'),
(3, 'Tenofovir', 'tablet', '300 mg'),
(4, 'Ceftriaxone', 'injection', '1 g'),
(5, 'Paracetamol', 'tablet', '500 mg'),
(6, 'Amlodipine', 'tablet', '5 mg');

INSERT INTO procedures(id, code, name, default_duration_min) VALUES
(1, 'PROC-ECG', 'Electrocardiography', 20),
(2, 'PROC-XR', 'Chest X-Ray', 25),
(3, 'PROC-BLD', 'Comprehensive Blood Panel', 15),
(4, 'PROC-IV', 'Intravenous Infusion', 60),
(5, 'PROC-US', 'Abdominal Ultrasound', 30),
(6, 'PROC-CNS', 'Infectious Disease Consultation', 40);

INSERT INTO treatment_items(id, encounter_id, procedure_id, medication_id, start_date, end_date, frequency, type, note) VALUES
(1, 1, NULL, 1, '2026-03-01', '2026-03-30', 'once_daily', 'medication', 'Antiretroviral base regimen'),
(2, 1, NULL, 2, '2026-03-01', '2026-03-30', 'once_daily', 'medication', 'Combined ART component'),
(3, 2, 6, NULL, '2026-03-06', '2026-03-06', 'one_time', 'procedure', 'Planned specialist follow-up'),
(4, 4, 4, NULL, '2026-03-10', '2026-03-10', 'one_time', 'procedure', 'Hydration support'),
(5, 6, NULL, 4, '2026-03-15', '2026-03-20', 'twice_daily', 'medication', 'Empirical antibacterial therapy'),
(6, 5, NULL, 6, '2026-03-12', '2026-04-12', 'once_daily', 'medication', 'Blood pressure control');
