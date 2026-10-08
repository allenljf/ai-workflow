-- Apply once as a migration owner in the selected schema, never the runtime role.
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;
DO $$ BEGIN
 IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='fde_app') THEN CREATE ROLE fde_app NOLOGIN NOSUPERUSER NOBYPASSRLS; END IF;
 IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='fde_worker') THEN CREATE ROLE fde_worker NOLOGIN NOSUPERUSER NOBYPASSRLS; END IF;
END $$;
CREATE TABLE schema_version(version integer PRIMARY KEY CHECK(version=1));
INSERT INTO schema_version VALUES(1);
CREATE TABLE jobs(id text PRIMARY KEY,tenant text NOT NULL,key text,payload text,status text,owner text,lease_until double precision,lease_version integer,attempts integer,max_attempts integer,deadline double precision,next_run double precision,cancel_requested integer,cost text,max_cost text,step text, UNIQUE(tenant,key));
CREATE TABLE receipts(job_id text REFERENCES jobs(id),step text,payload text,PRIMARY KEY(job_id,step));
CREATE TABLE local_effects(job_id text REFERENCES jobs(id),step text,payload text,PRIMARY KEY(job_id,step));
CREATE TABLE external_calls(job_id text REFERENCES jobs(id),step text,status text,PRIMARY KEY(job_id,step));
CREATE TABLE documents(tenant text,id text,version integer,text text,source_url text,PRIMARY KEY(tenant,id,version));
CREATE TABLE embedding_profile(singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),model text,digest text,dimensions integer CHECK(dimensions BETWEEN 1 AND 8192));
CREATE TABLE embeddings(tenant text,id text,version integer,vector vector,PRIMARY KEY(tenant,id,version),FOREIGN KEY(tenant,id,version) REFERENCES documents(tenant,id,version));
DO $$ DECLARE t text; BEGIN
 EXECUTE format('GRANT USAGE ON SCHEMA %I TO fde_app,fde_worker',current_schema());
 FOREACH t IN ARRAY ARRAY['jobs','documents','embeddings'] LOOP
  EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY',t);
  EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY',t);
  EXECUTE format('CREATE POLICY tenant ON %I TO fde_app USING (tenant=current_setting(''fde.tenant'',true)) WITH CHECK (tenant=current_setting(''fde.tenant'',true))',t);
  EXECUTE format('CREATE POLICY worker ON %I TO fde_worker USING (true) WITH CHECK (true)',t);
 END LOOP;
 FOREACH t IN ARRAY ARRAY['receipts','local_effects','external_calls'] LOOP
  EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY',t);
  EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY',t);
  EXECUTE format('CREATE POLICY tenant ON %I TO fde_app USING (EXISTS(SELECT 1 FROM jobs j WHERE j.id=job_id)) WITH CHECK (EXISTS(SELECT 1 FROM jobs j WHERE j.id=job_id))',t);
  EXECUTE format('CREATE POLICY worker ON %I TO fde_worker USING (true) WITH CHECK (true)',t);
 END LOOP;
END $$;
GRANT SELECT,INSERT,UPDATE ON jobs,receipts,local_effects,external_calls,documents,embeddings TO fde_app,fde_worker;
GRANT SELECT ON schema_version,embedding_profile TO fde_app,fde_worker;
GRANT INSERT ON embedding_profile TO fde_app,fde_worker;
-- One profile per schema binds model/digest/dimension. Create a new schema to re-embed.
-- Exact cosine via pgvector; add a fixed-dimension ANN index only after retrieval eval.
CREATE FUNCTION check_embedding_dimensions() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS (SELECT FROM embedding_profile WHERE dimensions=vector_dims(NEW.vector)) THEN
  RAISE EXCEPTION 'Embedding dimension/profile mismatch';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER embedding_dimensions BEFORE INSERT OR UPDATE ON embeddings FOR EACH ROW EXECUTE FUNCTION check_embedding_dimensions();
