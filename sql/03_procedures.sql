CREATE OR REPLACE FUNCTION get_doctor_patients(p_doctor_id int)
RETURNS TABLE(
  id int,
  name varchar,
  sex varchar,
  phone varchar,
  email varchar,
  snus varchar,
  passport varchar,
  birth_date date
)
LANGUAGE sql
AS $$
  SELECT DISTINCT p.id, p.name, p.sex, p.phone, p.email, p.snus, p.passport, p.birth_date
  FROM patients p
  JOIN encounters e ON e.patient_id = p.id
  WHERE e.doctor_id = p_doctor_id
  ORDER BY p.name
$$;
