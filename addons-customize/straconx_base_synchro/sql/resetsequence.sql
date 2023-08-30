CREATE FUNCTION resetseq_sequence_max_value(oid) RETURNS bigint
VOLATILE STRICT LANGUAGE plpgsql AS  $$
DECLARE
 tabrelid oid;
 colname name;
 r record;
 newmax bigint;
BEGIN
 FOR tabrelid, colname IN SELECT attrelid, attname
               FROM pg_attribute
              WHERE (attrelid, attnum) IN (
                      SELECT adrelid::regclass,adnum
                        FROM pg_attrdef
                       WHERE oid IN (SELECT objid
                                       FROM pg_depend
                                      WHERE refobjid = $1
                                            AND classid = 'pg_attrdef'::regclass
                                    )
          ) LOOP
      FOR r IN EXECUTE 'SELECT max(' || quote_ident(colname) || ') FROM ' || tabrelid::regclass LOOP
          IF newmax IS NULL OR r.max > newmax THEN
              newmax := 900000000;
          END IF;
      END LOOP;
  END LOOP;
  RETURN newmax;
END; $$ ;
COMMENT ON FUNCTION resetseq_sequence_max_value(oid) IS
'Returns the maximum value used in any column that uses this sequence as default';

CREATE TYPE resetseq_report_type AS (sequence_name text, value bigint);

CREATE FUNCTION resetseq_reset_sequences_in_table(regclass)
RETURNS setof resetseq_report_type
VOLATILE STRICT LANGUAGE SQL AS $$
SELECT refobjid::regclass::text, setval(refobjid, resetseq_sequence_max_value(refobjid))
  FROM pg_depend
 WHERE classid = 'pg_attrdef'::regclass AND
       refobjsubid = 0 AND
       objid IN (SELECT objid
                   FROM pg_depend
                  WHERE classid = 'pg_attrdef'::regclass AND
                        refclassid = 'pg_class'::regclass AND
                        refobjsubid > 0 AND
                        refobjid = $1);
$$;
COMMENT ON FUNCTION resetseq_reset_sequences_in_table(regclass) IS
'Reset all sequences used in a particular table';

CREATE FUNCTION resetseq_reset_sequences_in_schema(name)
RETURNS setof resetseq_report_type
VOLATILE STRICT LANGUAGE SQL AS $$
SELECT refobjid::text, setval(refobjid, resetseq_sequence_max_value(refobjid))
FROM (SELECT DISTINCT refobjid::regclass
        FROM pg_depend
       WHERE classid = 'pg_attrdef'::regclass AND
             refobjsubid = 0 AND
             objid IN (SELECT objid
                         FROM pg_depend JOIN pg_class ON pg_class.oid = pg_depend.refobjid
                              JOIN pg_namespace ON pg_class.relnamespace = pg_namespace.oid
                        WHERE classid = 'pg_attrdef'::regclass AND
                              refclassid = 'pg_class'::regclass AND
                              refobjsubid > 0 AND
                              nspname = $1 AND
                              relkind = 'r'
                      )
     ) f;
$$;
COMMENT ON FUNCTION resetseq_reset_sequences_in_schema(name) IS
'Reset all sequences used in tables in the given schema';

CREATE FUNCTION resetseq_reset_sequences_in_database()
RETURNS setof resetseq_report_type
VOLATILE STRICT LANGUAGE SQL AS $$
SELECT refobjid::text, setval(refobjid, resetseq_sequence_max_value(refobjid))
FROM (SELECT DISTINCT refobjid::regclass
        FROM pg_depend
       WHERE classid = 'pg_attrdef'::regclass AND
             refobjsubid = 0 AND
             objid IN (SELECT objid
                         FROM pg_depend JOIN pg_class ON pg_class.oid = pg_depend.refobjid
                        WHERE classid = 'pg_attrdef'::regclass AND
                              refclassid = 'pg_class'::regclass AND
                              refobjsubid > 0 AND
                              relkind = 'r'
                      )
     ) f;
$$;
COMMENT ON FUNCTION resetseq_reset_sequences_in_database() IS
'Reset all sequences used in tables in the current database';
