CREATE OR REPLACE FUNCTION validate_treatment_item_xor()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF (NEW.procedure_id IS NULL AND NEW.medication_id IS NULL) OR (NEW.procedure_id IS NOT NULL AND NEW.medication_id IS NOT NULL) THEN
    RAISE EXCEPTION 'Exactly one of procedure_id or medication_id must be set';
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_treatment_item_xor ON treatment_items;

CREATE TRIGGER trg_treatment_item_xor
BEFORE INSERT OR UPDATE ON treatment_items
FOR EACH ROW
EXECUTE FUNCTION validate_treatment_item_xor();
