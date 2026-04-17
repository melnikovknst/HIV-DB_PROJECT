CREATE TABLE IF NOT EXISTS medical_institutions(
  id int PRIMARY KEY,
  name varchar NOT NULL,
  type varchar NOT NULL,
  phone varchar NOT NULL,
  email varchar NOT NULL
);

CREATE TABLE IF NOT EXISTS departments(
  id int PRIMARY KEY,
  name varchar NOT NULL,
  phone varchar NOT NULL,
  type varchar NOT NULL,
  institution_id int NOT NULL REFERENCES medical_institutions(id)
);

CREATE TABLE IF NOT EXISTS beds(
  id int PRIMARY KEY,
  status varchar NOT NULL,
  department_id int NOT NULL REFERENCES departments(id)
);

CREATE TABLE IF NOT EXISTS staff(
  id int PRIMARY KEY,
  department_id int NOT NULL REFERENCES departments(id),
  name varchar NOT NULL,
  phone varchar NOT NULL,
  email varchar NOT NULL,
  hire_date date NOT NULL,
  staff_type varchar NOT NULL,
  is_active boolean NOT NULL,
  inn varchar NOT NULL
);

CREATE TABLE IF NOT EXISTS doctors(
  id int PRIMARY KEY REFERENCES staff(id),
  experience_years int NOT NULL,
  license_number varchar
);

CREATE TABLE IF NOT EXISTS specializations(
  id int PRIMARY KEY,
  code varchar NOT NULL,
  name varchar NOT NULL
);

CREATE TABLE IF NOT EXISTS doctors_specializations(
  doctor_id int NOT NULL REFERENCES doctors(id),
  specialization_id int NOT NULL REFERENCES specializations(id),
  PRIMARY KEY(doctor_id, specialization_id)
);

CREATE TABLE IF NOT EXISTS patients(
  id int PRIMARY KEY,
  name varchar NOT NULL,
  sex varchar NOT NULL,
  phone varchar NOT NULL,
  email varchar NOT NULL,
  snus varchar NOT NULL,
  passport varchar NOT NULL,
  birth_date date NOT NULL
);

CREATE TABLE IF NOT EXISTS encounters(
  id int PRIMARY KEY,
  patient_id int NOT NULL REFERENCES patients(id),
  doctor_id int NOT NULL REFERENCES doctors(id),
  bed_id int REFERENCES beds(id),
  type varchar NOT NULL,
  start_datetime timestamp NOT NULL,
  end_datetime timestamp NOT NULL
);

CREATE TABLE IF NOT EXISTS diagnoses(
  id int PRIMARY KEY,
  patient_id int NOT NULL REFERENCES patients(id),
  encounter_id int NOT NULL REFERENCES encounters(id),
  icd10_code varchar NOT NULL,
  diagnosis_type varchar NOT NULL,
  diagnosed_at timestamp NOT NULL,
  notes varchar NOT NULL
);

CREATE TABLE IF NOT EXISTS medication(
  id int PRIMARY KEY,
  name varchar NOT NULL,
  form varchar NOT NULL,
  strength varchar NOT NULL
);

CREATE TABLE IF NOT EXISTS procedures(
  id int PRIMARY KEY,
  code varchar NOT NULL,
  name varchar NOT NULL,
  default_duration_min int NOT NULL
);

CREATE TABLE IF NOT EXISTS treatment_items(
  id int PRIMARY KEY,
  encounter_id int NOT NULL REFERENCES encounters(id),
  procedure_id int REFERENCES procedures(id),
  medication_id int REFERENCES medication(id),
  start_date date NOT NULL,
  end_date date NOT NULL,
  frequency varchar NOT NULL,
  type varchar NOT NULL,
  note varchar NOT NULL
);
