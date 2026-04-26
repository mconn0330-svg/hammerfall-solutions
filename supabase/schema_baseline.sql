


SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


CREATE SCHEMA IF NOT EXISTS "public";


ALTER SCHEMA "public" OWNER TO "pg_database_owner";


COMMENT ON SCHEMA "public" IS 'standard public schema';


SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "public"."helm_entities" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "entity_type" "text" NOT NULL,
    "name" "text" NOT NULL,
    "attributes" "jsonb" DEFAULT '{}'::"jsonb",
    "first_seen" timestamp with time zone DEFAULT "now"(),
    "last_updated" timestamp with time zone DEFAULT "now"(),
    "summary" "text",
    "active" boolean DEFAULT true NOT NULL,
    "aliases" "text"[] DEFAULT '{}'::"text"[],
    "embedding" "extensions"."vector"(1536)
);


ALTER TABLE "public"."helm_entities" OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."find_entity_by_alias"("search_name" "text") RETURNS SETOF "public"."helm_entities"
    LANGUAGE "sql" STABLE SECURITY DEFINER
    AS $$
  SELECT * FROM helm_entities
  WHERE LOWER(name) = LOWER(search_name)
  OR EXISTS (
    SELECT 1 FROM unnest(aliases) AS a
    WHERE LOWER(a) = LOWER(search_name)
  );
$$;


ALTER FUNCTION "public"."find_entity_by_alias"("search_name" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."match_beliefs"("query_embedding" "extensions"."vector", "match_threshold" double precision DEFAULT 0.7, "match_count" integer DEFAULT 10) RETURNS TABLE("id" "uuid", "domain" "text", "belief" "text", "strength" double precision, "active" boolean, "created_at" timestamp with time zone, "similarity" double precision)
    LANGUAGE "sql" STABLE
    SET "search_path" TO 'extensions', 'public'
    AS $$
  SELECT
    id, domain, belief, strength, active, created_at,
    1 - (embedding <=> query_embedding) AS similarity
  FROM helm_beliefs
  WHERE active = true
    AND embedding IS NOT NULL
    AND 1 - (embedding <=> query_embedding) > match_threshold
  ORDER BY embedding <=> query_embedding
  LIMIT match_count;
$$;


ALTER FUNCTION "public"."match_beliefs"("query_embedding" "extensions"."vector", "match_threshold" double precision, "match_count" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."match_entities"("query_embedding" "extensions"."vector", "match_threshold" double precision DEFAULT 0.7, "match_count" integer DEFAULT 10) RETURNS TABLE("id" "uuid", "entity_type" "text", "name" "text", "summary" "text", "attributes" "jsonb", "first_seen" timestamp with time zone, "similarity" double precision)
    LANGUAGE "sql" STABLE
    SET "search_path" TO 'extensions', 'public'
    AS $$
  SELECT
    id, entity_type, name, summary, attributes, first_seen,
    1 - (embedding <=> query_embedding) AS similarity
  FROM helm_entities
  WHERE active = true
    AND embedding IS NOT NULL
    AND 1 - (embedding <=> query_embedding) > match_threshold
  ORDER BY embedding <=> query_embedding
  LIMIT match_count;
$$;


ALTER FUNCTION "public"."match_entities"("query_embedding" "extensions"."vector", "match_threshold" double precision, "match_count" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."match_memories"("query_embedding" "extensions"."vector", "match_threshold" double precision DEFAULT 0.7, "match_count" integer DEFAULT 10, "filter_project" "text" DEFAULT 'hammerfall-solutions'::"text", "filter_agent" "text" DEFAULT 'helm'::"text") RETURNS TABLE("id" "uuid", "content" "text", "memory_type" "text", "confidence" double precision, "session_date" "date", "created_at" timestamp with time zone, "similarity" double precision)
    LANGUAGE "sql" STABLE
    SET "search_path" TO 'extensions', 'public'
    AS $$
  SELECT
    id, content, memory_type, confidence, session_date, created_at,
    1 - (embedding <=> query_embedding) AS similarity
  FROM helm_memory
  WHERE project = filter_project
    AND agent   = filter_agent
    AND embedding IS NOT NULL
    AND 1 - (embedding <=> query_embedding) > match_threshold
  ORDER BY embedding <=> query_embedding
  LIMIT match_count;
$$;


ALTER FUNCTION "public"."match_memories"("query_embedding" "extensions"."vector", "match_threshold" double precision, "match_count" integer, "filter_project" "text", "filter_agent" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."rls_auto_enable"() RETURNS "event_trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'pg_catalog'
    AS $$
DECLARE
  cmd record;
BEGIN
  FOR cmd IN
    SELECT *
    FROM pg_event_trigger_ddl_commands()
    WHERE command_tag IN ('CREATE TABLE', 'CREATE TABLE AS', 'SELECT INTO')
      AND object_type IN ('table','partitioned table')
  LOOP
     IF cmd.schema_name IS NOT NULL AND cmd.schema_name IN ('public') AND cmd.schema_name NOT IN ('pg_catalog','information_schema') AND cmd.schema_name NOT LIKE 'pg_toast%' AND cmd.schema_name NOT LIKE 'pg_temp%' THEN
      BEGIN
        EXECUTE format('alter table if exists %s enable row level security', cmd.object_identity);
        RAISE LOG 'rls_auto_enable: enabled RLS on %', cmd.object_identity;
      EXCEPTION
        WHEN OTHERS THEN
          RAISE LOG 'rls_auto_enable: failed to enable RLS on %', cmd.object_identity;
      END;
     ELSE
        RAISE LOG 'rls_auto_enable: skip % (either system schema or not in enforced list: %.)', cmd.object_identity, cmd.schema_name;
     END IF;
  END LOOP;
END;
$$;


ALTER FUNCTION "public"."rls_auto_enable"() OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."helm_beliefs" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "domain" "text" NOT NULL,
    "belief" "text" NOT NULL,
    "strength" double precision DEFAULT 0.7,
    "active" boolean DEFAULT true,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "source" "text" DEFAULT 'seeded'::"text" NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "embedding" "extensions"."vector"(1536),
    CONSTRAINT "helm_beliefs_strength_check" CHECK ((("strength" >= (0.0)::double precision) AND ("strength" <= (1.0)::double precision)))
);


ALTER TABLE "public"."helm_beliefs" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."helm_entity_relationships" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "from_entity" "uuid" NOT NULL,
    "to_entity" "uuid" NOT NULL,
    "relationship" "text" NOT NULL,
    "notes" "text",
    "active" boolean DEFAULT true NOT NULL,
    "strength" double precision,
    "created_at" timestamp with time zone DEFAULT "now"(),
    CONSTRAINT "helm_entity_relationships_strength_check" CHECK ((("strength" IS NULL) OR (("strength" >= (0.0)::double precision) AND ("strength" <= (1.0)::double precision)))),
    CONSTRAINT "no_self_relationship" CHECK (("from_entity" <> "to_entity"))
);


ALTER TABLE "public"."helm_entity_relationships" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."helm_frames" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "session_id" "uuid" NOT NULL,
    "turn_number" integer NOT NULL,
    "layer" "text" DEFAULT 'warm'::"text" NOT NULL,
    "frame_json" "jsonb" NOT NULL,
    "frame_status" "text" DEFAULT 'active'::"text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"(),
    CONSTRAINT "helm_frames_frame_status_check" CHECK (("frame_status" = ANY (ARRAY['active'::"text", 'superseded'::"text", 'canonical'::"text"]))),
    CONSTRAINT "helm_frames_layer_check" CHECK (("layer" = ANY (ARRAY['hot'::"text", 'warm'::"text", 'cold'::"text"])))
);


ALTER TABLE "public"."helm_frames" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."helm_memory" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "project" "text" NOT NULL,
    "agent" "text" NOT NULL,
    "memory_type" "text" NOT NULL,
    "content" "text" NOT NULL,
    "sync_ready" boolean DEFAULT false,
    "synced_to_core" boolean DEFAULT false,
    "session_date" "date" DEFAULT CURRENT_DATE,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "full_content" "jsonb",
    "confidence" double precision,
    "subject_ref" "uuid",
    "embedding" "extensions"."vector"(1536),
    CONSTRAINT "helm_memory_confidence_check" CHECK ((("confidence" IS NULL) OR (("confidence" >= (0.0)::double precision) AND ("confidence" <= (1.0)::double precision)))),
    CONSTRAINT "helm_memory_memory_type_check" CHECK (("memory_type" = ANY (ARRAY['behavioral'::"text", 'scratchpad'::"text", 'archive'::"text", 'sync'::"text", 'monologue'::"text", 'coherence_check'::"text", 'external_knowledge'::"text", 'reasoning'::"text", 'heartbeat'::"text", 'frame'::"text"])))
);


ALTER TABLE "public"."helm_memory" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."helm_memory_index" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "project" "text" NOT NULL,
    "agent" "text" NOT NULL,
    "category" "text" NOT NULL,
    "summary" "text" NOT NULL,
    "entry_count" integer DEFAULT 0,
    "date_range_start" "date",
    "date_range_end" "date",
    "last_updated" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."helm_memory_index" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."helm_personality" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "attribute" "text" NOT NULL,
    "score" double precision DEFAULT 0.5 NOT NULL,
    "description" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    CONSTRAINT "helm_personality_score_check" CHECK ((("score" >= (0.0)::double precision) AND ("score" <= (1.0)::double precision)))
);


ALTER TABLE "public"."helm_personality" OWNER TO "postgres";


ALTER TABLE ONLY "public"."helm_beliefs"
    ADD CONSTRAINT "helm_beliefs_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."helm_entities"
    ADD CONSTRAINT "helm_entities_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."helm_entity_relationships"
    ADD CONSTRAINT "helm_entity_relationships_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."helm_frames"
    ADD CONSTRAINT "helm_frames_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."helm_frames"
    ADD CONSTRAINT "helm_frames_session_id_turn_number_key" UNIQUE ("session_id", "turn_number");



ALTER TABLE ONLY "public"."helm_memory_index"
    ADD CONSTRAINT "helm_memory_index_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."helm_memory_index"
    ADD CONSTRAINT "helm_memory_index_project_agent_category_key" UNIQUE ("project", "agent", "category");



ALTER TABLE ONLY "public"."helm_memory"
    ADD CONSTRAINT "helm_memory_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."helm_personality"
    ADD CONSTRAINT "helm_personality_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."helm_personality"
    ADD CONSTRAINT "uq_personality_attribute" UNIQUE ("attribute");



CREATE INDEX "helm_beliefs_embedding_idx" ON "public"."helm_beliefs" USING "hnsw" ("embedding" "extensions"."vector_cosine_ops") WITH ("m"='16', "ef_construction"='64');



CREATE INDEX "helm_entities_embedding_idx" ON "public"."helm_entities" USING "hnsw" ("embedding" "extensions"."vector_cosine_ops") WITH ("m"='16', "ef_construction"='64');



CREATE INDEX "helm_memory_embedding_idx" ON "public"."helm_memory" USING "hnsw" ("embedding" "extensions"."vector_cosine_ops") WITH ("m"='16', "ef_construction"='64');



CREATE INDEX "idx_beliefs_active" ON "public"."helm_beliefs" USING "btree" ("active");



CREATE INDEX "idx_beliefs_domain" ON "public"."helm_beliefs" USING "btree" ("domain");



CREATE INDEX "idx_beliefs_strength" ON "public"."helm_beliefs" USING "btree" ("strength");



CREATE INDEX "idx_entities_aliases" ON "public"."helm_entities" USING "gin" ("aliases");



CREATE INDEX "idx_entities_name" ON "public"."helm_entities" USING "btree" ("name");



CREATE INDEX "idx_entities_type" ON "public"."helm_entities" USING "btree" ("entity_type");



CREATE INDEX "idx_helm_frames_layer" ON "public"."helm_frames" USING "btree" ("layer");



CREATE INDEX "idx_helm_frames_session" ON "public"."helm_frames" USING "btree" ("session_id");



CREATE INDEX "idx_helm_frames_session_turn" ON "public"."helm_frames" USING "btree" ("session_id", "turn_number");



CREATE INDEX "idx_helm_memory_project" ON "public"."helm_memory" USING "btree" ("project");



CREATE INDEX "idx_helm_memory_sync_ready" ON "public"."helm_memory" USING "btree" ("sync_ready") WHERE ("sync_ready" = true);



CREATE INDEX "idx_helm_memory_type" ON "public"."helm_memory" USING "btree" ("project", "agent", "memory_type");



CREATE INDEX "idx_memory_index_project" ON "public"."helm_memory_index" USING "btree" ("project", "agent");



CREATE INDEX "idx_rel_active" ON "public"."helm_entity_relationships" USING "btree" ("active");



CREATE INDEX "idx_rel_from" ON "public"."helm_entity_relationships" USING "btree" ("from_entity");



CREATE INDEX "idx_rel_to" ON "public"."helm_entity_relationships" USING "btree" ("to_entity");



ALTER TABLE ONLY "public"."helm_memory"
    ADD CONSTRAINT "fk_subject" FOREIGN KEY ("subject_ref") REFERENCES "public"."helm_entities"("id");



ALTER TABLE ONLY "public"."helm_entity_relationships"
    ADD CONSTRAINT "helm_entity_relationships_from_entity_fkey" FOREIGN KEY ("from_entity") REFERENCES "public"."helm_entities"("id");



ALTER TABLE ONLY "public"."helm_entity_relationships"
    ADD CONSTRAINT "helm_entity_relationships_to_entity_fkey" FOREIGN KEY ("to_entity") REFERENCES "public"."helm_entities"("id");



CREATE POLICY "anon_read_helm_beliefs" ON "public"."helm_beliefs" FOR SELECT TO "anon" USING (true);



CREATE POLICY "anon_read_helm_entities" ON "public"."helm_entities" FOR SELECT TO "anon" USING (true);



CREATE POLICY "anon_read_helm_entity_relationships" ON "public"."helm_entity_relationships" FOR SELECT TO "anon" USING (true);



CREATE POLICY "anon_read_helm_frames" ON "public"."helm_frames" FOR SELECT TO "anon" USING (true);



CREATE POLICY "anon_read_helm_memory" ON "public"."helm_memory" FOR SELECT TO "anon" USING (true);



CREATE POLICY "anon_read_helm_memory_index" ON "public"."helm_memory_index" FOR SELECT TO "anon" USING (true);



CREATE POLICY "anon_read_helm_personality" ON "public"."helm_personality" FOR SELECT TO "anon" USING (true);



CREATE POLICY "anon_update_helm_personality" ON "public"."helm_personality" FOR UPDATE TO "anon" USING (true) WITH CHECK (true);



ALTER TABLE "public"."helm_beliefs" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."helm_entities" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."helm_entity_relationships" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."helm_frames" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."helm_memory" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."helm_memory_index" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."helm_personality" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "service_role_full_access" ON "public"."helm_entity_relationships" TO "service_role" USING (true) WITH CHECK (true);



CREATE POLICY "service_role_full_access" ON "public"."helm_frames" USING (true) WITH CHECK (true);



CREATE POLICY "service_role_full_access" ON "public"."helm_memory" USING (true) WITH CHECK (true);



CREATE POLICY "service_role_full_access" ON "public"."helm_memory_index" USING (true) WITH CHECK (true);



GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";



GRANT ALL ON TABLE "public"."helm_entities" TO "anon";
GRANT ALL ON TABLE "public"."helm_entities" TO "authenticated";
GRANT ALL ON TABLE "public"."helm_entities" TO "service_role";



GRANT ALL ON FUNCTION "public"."find_entity_by_alias"("search_name" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."find_entity_by_alias"("search_name" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."find_entity_by_alias"("search_name" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."match_beliefs"("query_embedding" "extensions"."vector", "match_threshold" double precision, "match_count" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."match_beliefs"("query_embedding" "extensions"."vector", "match_threshold" double precision, "match_count" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."match_beliefs"("query_embedding" "extensions"."vector", "match_threshold" double precision, "match_count" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."match_entities"("query_embedding" "extensions"."vector", "match_threshold" double precision, "match_count" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."match_entities"("query_embedding" "extensions"."vector", "match_threshold" double precision, "match_count" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."match_entities"("query_embedding" "extensions"."vector", "match_threshold" double precision, "match_count" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."match_memories"("query_embedding" "extensions"."vector", "match_threshold" double precision, "match_count" integer, "filter_project" "text", "filter_agent" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."match_memories"("query_embedding" "extensions"."vector", "match_threshold" double precision, "match_count" integer, "filter_project" "text", "filter_agent" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."match_memories"("query_embedding" "extensions"."vector", "match_threshold" double precision, "match_count" integer, "filter_project" "text", "filter_agent" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."rls_auto_enable"() TO "anon";
GRANT ALL ON FUNCTION "public"."rls_auto_enable"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."rls_auto_enable"() TO "service_role";



GRANT ALL ON TABLE "public"."helm_beliefs" TO "anon";
GRANT ALL ON TABLE "public"."helm_beliefs" TO "authenticated";
GRANT ALL ON TABLE "public"."helm_beliefs" TO "service_role";



GRANT ALL ON TABLE "public"."helm_entity_relationships" TO "anon";
GRANT ALL ON TABLE "public"."helm_entity_relationships" TO "authenticated";
GRANT ALL ON TABLE "public"."helm_entity_relationships" TO "service_role";



GRANT ALL ON TABLE "public"."helm_frames" TO "anon";
GRANT ALL ON TABLE "public"."helm_frames" TO "authenticated";
GRANT ALL ON TABLE "public"."helm_frames" TO "service_role";



GRANT ALL ON TABLE "public"."helm_memory" TO "anon";
GRANT ALL ON TABLE "public"."helm_memory" TO "authenticated";
GRANT ALL ON TABLE "public"."helm_memory" TO "service_role";



GRANT ALL ON TABLE "public"."helm_memory_index" TO "anon";
GRANT ALL ON TABLE "public"."helm_memory_index" TO "authenticated";
GRANT ALL ON TABLE "public"."helm_memory_index" TO "service_role";



GRANT ALL ON TABLE "public"."helm_personality" TO "anon";
GRANT ALL ON TABLE "public"."helm_personality" TO "authenticated";
GRANT ALL ON TABLE "public"."helm_personality" TO "service_role";



ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "service_role";
