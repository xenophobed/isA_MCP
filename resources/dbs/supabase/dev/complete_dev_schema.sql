--
-- PostgreSQL database dump
--

-- Dumped from database version 17.4
-- Dumped by pg_dump version 17.5 (Debian 17.5-1.pgdg120+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: dev; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA dev;


--
-- Name: cleanup_expired_memories(); Type: FUNCTION; Schema: dev; Owner: -
--

CREATE FUNCTION dev.cleanup_expired_memories() RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    expired_count INTEGER;
BEGIN
    -- 清理过期的工作记忆
    WITH expired_memories AS (
        UPDATE dev.working_memories 
        SET is_active = false 
        WHERE expires_at < NOW() AND is_active = true
        RETURNING id
    )
    SELECT COUNT(*) INTO expired_count FROM expired_memories;
    
    -- 更新元数据
    UPDATE dev.memory_metadata 
    SET lifecycle_stage = 'archived', updated_at = NOW()
    WHERE memory_type = 'working' 
    AND memory_id IN (
        SELECT id FROM dev.working_memories 
        WHERE expires_at < NOW() AND is_active = false
    );
    
    RETURN expired_count;
END;
$$;


--
-- Name: cleanup_old_metadata_embeddings(integer, text); Type: FUNCTION; Schema: dev; Owner: -
--

CREATE FUNCTION dev.cleanup_old_metadata_embeddings(days_old integer DEFAULT 30, database_name text DEFAULT NULL::text) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    deleted_count integer;
BEGIN
    DELETE FROM dev.db_meta_embedding 
    WHERE created_at < NOW() - INTERVAL '1 day' * days_old
    AND (database_name IS NULL OR database_source = database_name);
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$;


--
-- Name: find_similar_entities(text, text, double precision, integer); Type: FUNCTION; Schema: dev; Owner: -
--

CREATE FUNCTION dev.find_similar_entities(entity_name_pattern text, entity_type_filter text DEFAULT NULL::text, similarity_threshold double precision DEFAULT 0.7, result_limit integer DEFAULT 5) RETURNS TABLE(id text, entity_type text, entity_name text, content text, confidence_score double precision, semantic_tags text[])
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id,
        e.entity_type,
        e.entity_name,
        e.content,
        e.confidence_score,
        e.semantic_tags
    FROM dev.db_meta_embedding e
    WHERE 
        (entity_type_filter IS NULL OR e.entity_type = entity_type_filter)
        AND (
            SIMILARITY(e.entity_name, entity_name_pattern) > similarity_threshold
            OR e.entity_name ILIKE '%' || entity_name_pattern || '%'
        )
    ORDER BY SIMILARITY(e.entity_name, entity_name_pattern) DESC
    LIMIT result_limit;
END;
$$;


--
-- Name: get_metadata_stats(text); Type: FUNCTION; Schema: dev; Owner: -
--

CREATE FUNCTION dev.get_metadata_stats(database_name text DEFAULT NULL::text) RETURNS TABLE(entity_type text, total_entities bigint, avg_confidence double precision, total_semantic_tags bigint)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e.entity_type,
        COUNT(*) as total_entities,
        AVG(e.confidence_score) as avg_confidence,
        SUM(array_length(e.semantic_tags, 1)) as total_semantic_tags
    FROM dev.db_meta_embedding e
    WHERE (database_name IS NULL OR e.database_source = database_name)
    GROUP BY e.entity_type
    ORDER BY total_entities DESC;
END;
$$;


--
-- Name: match_metadata_embeddings(public.vector, double precision, integer, text, text, double precision); Type: FUNCTION; Schema: dev; Owner: -
--

CREATE FUNCTION dev.match_metadata_embeddings(query_embedding public.vector, match_threshold double precision DEFAULT 0.0, match_count integer DEFAULT 10, entity_type_filter text DEFAULT NULL::text, database_filter text DEFAULT NULL::text, min_confidence double precision DEFAULT 0.0) RETURNS TABLE(id text, entity_type text, entity_name text, entity_full_name text, content text, metadata jsonb, semantic_tags text[], confidence_score double precision, database_source text, created_at timestamp with time zone, similarity double precision)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id,
        e.entity_type,
        e.entity_name,
        e.entity_full_name,
        e.content,
        e.metadata,
        e.semantic_tags,
        e.confidence_score,
        e.database_source,
        e.created_at,
        1 - (e.embedding <=> query_embedding) AS similarity
    FROM dev.db_meta_embedding e
    WHERE 
        (entity_type_filter IS NULL OR e.entity_type = entity_type_filter)
        AND (database_filter IS NULL OR e.database_source = database_filter)
        AND e.confidence_score >= min_confidence
        AND 1 - (e.embedding <=> query_embedding) > match_threshold
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;


--
-- Name: search_memories_by_similarity(character varying, public.vector, text[], integer, double precision); Type: FUNCTION; Schema: dev; Owner: -
--

CREATE FUNCTION dev.search_memories_by_similarity(p_user_id character varying, p_query_embedding public.vector, p_memory_types text[] DEFAULT ARRAY['factual'::text, 'procedural'::text, 'episodic'::text, 'semantic'::text], p_limit integer DEFAULT 10, p_threshold double precision DEFAULT 0.7) RETURNS TABLE(memory_type text, memory_id uuid, content text, similarity double precision)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    (
        SELECT 'factual'::TEXT, f.id, f.subject || ': ' || f.object_value, 1 - (f.embedding <=> p_query_embedding)
        FROM dev.factual_memories f
        WHERE f.user_id = p_user_id 
        AND f.is_active = true
        AND f.embedding IS NOT NULL
        AND 'factual' = ANY(p_memory_types)
        AND 1 - (f.embedding <=> p_query_embedding) > p_threshold
        
        UNION ALL
        
        SELECT 'procedural'::TEXT, pr.id, pr.procedure_name, 1 - (pr.embedding <=> p_query_embedding)
        FROM dev.procedural_memories pr
        WHERE pr.user_id = p_user_id
        AND pr.embedding IS NOT NULL
        AND 'procedural' = ANY(p_memory_types)
        AND 1 - (pr.embedding <=> p_query_embedding) > p_threshold
        
        UNION ALL
        
        SELECT 'episodic'::TEXT, e.id, e.episode_title, 1 - (e.embedding <=> p_query_embedding)
        FROM dev.episodic_memories e
        WHERE e.user_id = p_user_id
        AND e.embedding IS NOT NULL
        AND 'episodic' = ANY(p_memory_types)
        AND 1 - (e.embedding <=> p_query_embedding) > p_threshold
        
        UNION ALL
        
        SELECT 'semantic'::TEXT, s.id, s.concept_name || ': ' || s.definition, 1 - (s.embedding <=> p_query_embedding)
        FROM dev.semantic_memories s
        WHERE s.user_id = p_user_id
        AND s.embedding IS NOT NULL
        AND 'semantic' = ANY(p_memory_types)
        AND 1 - (s.embedding <=> p_query_embedding) > p_threshold
    )
    ORDER BY similarity DESC
    LIMIT p_limit;
END;
$$;


--
-- Name: track_memory_access(character varying, character varying, uuid); Type: FUNCTION; Schema: dev; Owner: -
--

CREATE FUNCTION dev.track_memory_access(p_user_id character varying, p_memory_type character varying, p_memory_id uuid) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- 更新元数据中的访问统计
    INSERT INTO dev.memory_metadata (user_id, memory_type, memory_id, access_count, last_accessed_at)
    VALUES (p_user_id, p_memory_type, p_memory_id, 1, NOW())
    ON CONFLICT (user_id, memory_type, memory_id)
    DO UPDATE SET
        access_count = dev.memory_metadata.access_count + 1,
        last_accessed_at = NOW(),
        updated_at = NOW();
END;
$$;


--
-- Name: update_memory_metadata(); Type: FUNCTION; Schema: dev; Owner: -
--

CREATE FUNCTION dev.update_memory_metadata() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    memory_type_value VARCHAR(20);
BEGIN
    -- 根据表名映射到正确的memory_type
    CASE TG_TABLE_NAME
        WHEN 'factual_memories' THEN memory_type_value := 'factual';
        WHEN 'procedural_memories' THEN memory_type_value := 'procedural';
        WHEN 'episodic_memories' THEN memory_type_value := 'episodic';
        WHEN 'semantic_memories' THEN memory_type_value := 'semantic';
        WHEN 'working_memories' THEN memory_type_value := 'working';
        ELSE memory_type_value := 'unknown';
    END CASE;
    
    -- 更新或插入元数据
    INSERT INTO dev.memory_metadata (user_id, memory_type, memory_id, modification_count, last_modified_at, version)
    VALUES (NEW.user_id, memory_type_value, NEW.id, 1, NOW(), 1)
    ON CONFLICT (user_id, memory_type, memory_id)
    DO UPDATE SET
        modification_count = dev.memory_metadata.modification_count + 1,
        last_modified_at = NOW(),
        version = dev.memory_metadata.version + 1,
        updated_at = NOW();
    
    RETURN NEW;
END;
$$;


--
-- Name: update_metadata_embedding_updated_at(); Type: FUNCTION; Schema: dev; Owner: -
--

CREATE FUNCTION dev.update_metadata_embedding_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: dev; Owner: -
--

CREATE FUNCTION dev.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: carts; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.carts (
    id integer NOT NULL,
    cart_id character varying(255) NOT NULL,
    user_id character varying(255),
    cart_data jsonb DEFAULT '{}'::jsonb,
    total_amount numeric(10,2) DEFAULT 0.00,
    currency character varying(3) DEFAULT 'USD'::character varying,
    status character varying(50) DEFAULT 'active'::character varying,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    expires_at timestamp with time zone
);


--
-- Name: carts_id_seq; Type: SEQUENCE; Schema: dev; Owner: -
--

CREATE SEQUENCE dev.carts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: carts_id_seq; Type: SEQUENCE OWNED BY; Schema: dev; Owner: -
--

ALTER SEQUENCE dev.carts_id_seq OWNED BY dev.carts.id;


--
-- Name: checkpoint_blobs; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.checkpoint_blobs (
    thread_id text NOT NULL,
    checkpoint_ns text DEFAULT ''::text NOT NULL,
    channel text NOT NULL,
    version text NOT NULL,
    type text NOT NULL,
    blob bytea
);


--
-- Name: checkpoint_migrations; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.checkpoint_migrations (
    v integer NOT NULL
);


--
-- Name: checkpoint_writes; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.checkpoint_writes (
    thread_id text NOT NULL,
    checkpoint_ns text DEFAULT ''::text NOT NULL,
    checkpoint_id text NOT NULL,
    task_id text NOT NULL,
    idx integer NOT NULL,
    channel text NOT NULL,
    type text,
    blob bytea NOT NULL,
    task_path text DEFAULT ''::text NOT NULL
);


--
-- Name: checkpoints; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.checkpoints (
    thread_id text NOT NULL,
    checkpoint_ns text DEFAULT ''::text NOT NULL,
    checkpoint_id text NOT NULL,
    parent_checkpoint_id text,
    type text,
    checkpoint jsonb NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL
);


--
-- Name: db_meta_embedding; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.db_meta_embedding (
    id text NOT NULL,
    entity_type text NOT NULL,
    entity_name text NOT NULL,
    entity_full_name text NOT NULL,
    content text NOT NULL,
    embedding public.vector(1536),
    metadata jsonb DEFAULT '{}'::jsonb,
    semantic_tags text[] DEFAULT '{}'::text[],
    confidence_score double precision DEFAULT 0.0,
    source_step integer DEFAULT 2,
    database_source text DEFAULT ''::text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: episodic_memories; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.episodic_memories (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id character varying(255),
    episode_title character varying(300) NOT NULL,
    summary text NOT NULL,
    participants jsonb DEFAULT '[]'::jsonb,
    location character varying(200),
    temporal_context character varying(100),
    key_events jsonb NOT NULL,
    emotional_context character varying(50),
    outcomes jsonb DEFAULT '[]'::jsonb,
    lessons_learned text,
    embedding public.vector(1536),
    emotional_intensity double precision DEFAULT 0.5,
    recall_frequency integer DEFAULT 0,
    last_recalled_at timestamp with time zone,
    occurred_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT episodic_memories_emotional_intensity_check CHECK (((emotional_intensity >= (0)::double precision) AND (emotional_intensity <= (1)::double precision)))
);


--
-- Name: events; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.events (
    id integer NOT NULL,
    event_id uuid DEFAULT extensions.uuid_generate_v4(),
    task_id uuid,
    user_id character varying(255),
    event_type character varying(100) NOT NULL,
    event_data jsonb,
    source character varying(100) DEFAULT 'event_sourcing_service'::character varying,
    priority integer DEFAULT 1,
    processed boolean DEFAULT false,
    processed_at timestamp with time zone,
    agent_response jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: events_id_seq; Type: SEQUENCE; Schema: dev; Owner: -
--

CREATE SEQUENCE dev.events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: events_id_seq; Type: SEQUENCE OWNED BY; Schema: dev; Owner: -
--

ALTER SEQUENCE dev.events_id_seq OWNED BY dev.events.id;


--
-- Name: factual_memories; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.factual_memories (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id character varying(255),
    fact_type character varying(50) NOT NULL,
    subject character varying(200) NOT NULL,
    predicate character varying(200) NOT NULL,
    object_value text NOT NULL,
    context text,
    confidence double precision DEFAULT 0.8,
    source_interaction_id uuid,
    embedding public.vector(1536),
    importance_score double precision DEFAULT 0.5,
    last_confirmed_at timestamp with time zone DEFAULT now(),
    expires_at timestamp with time zone,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT factual_memories_confidence_check CHECK (((confidence >= (0)::double precision) AND (confidence <= (1)::double precision)))
);


--
-- Name: langgraph_executions; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.langgraph_executions (
    id integer NOT NULL,
    trace_id character varying(255),
    span_id character varying(255),
    user_id character varying(255),
    node_name character varying(255),
    execution_order integer,
    input_state jsonb,
    output_state jsonb,
    next_action character varying(255),
    execution_time double precision,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: langgraph_executions_id_seq; Type: SEQUENCE; Schema: dev; Owner: -
--

CREATE SEQUENCE dev.langgraph_executions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: langgraph_executions_id_seq; Type: SEQUENCE OWNED BY; Schema: dev; Owner: -
--

ALTER SEQUENCE dev.langgraph_executions_id_seq OWNED BY dev.langgraph_executions.id;


--
-- Name: mcp_prompts; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.mcp_prompts (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    category character varying(100),
    arguments jsonb DEFAULT '[]'::jsonb,
    content text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    last_modified timestamp with time zone DEFAULT now(),
    usage_count integer DEFAULT 0,
    is_active boolean DEFAULT true
);


--
-- Name: mcp_prompts_id_seq; Type: SEQUENCE; Schema: dev; Owner: -
--

CREATE SEQUENCE dev.mcp_prompts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: mcp_prompts_id_seq; Type: SEQUENCE OWNED BY; Schema: dev; Owner: -
--

ALTER SEQUENCE dev.mcp_prompts_id_seq OWNED BY dev.mcp_prompts.id;


--
-- Name: mcp_resources; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.mcp_resources (
    id integer NOT NULL,
    uri character varying(500) NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    resource_type character varying(100),
    mime_type character varying(100),
    size_bytes bigint DEFAULT 0,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    last_accessed timestamp with time zone,
    access_count integer DEFAULT 0,
    is_active boolean DEFAULT true
);


--
-- Name: mcp_resources_id_seq; Type: SEQUENCE; Schema: dev; Owner: -
--

CREATE SEQUENCE dev.mcp_resources_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: mcp_resources_id_seq; Type: SEQUENCE OWNED BY; Schema: dev; Owner: -
--

ALTER SEQUENCE dev.mcp_resources_id_seq OWNED BY dev.mcp_resources.id;


--
-- Name: mcp_search_history; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.mcp_search_history (
    id integer NOT NULL,
    query text NOT NULL,
    filters jsonb,
    results_count integer,
    top_results text[],
    result_types text[],
    user_id text,
    session_id text,
    response_time_ms integer,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: mcp_search_analytics; Type: VIEW; Schema: dev; Owner: -
--

CREATE VIEW dev.mcp_search_analytics AS
 SELECT date_trunc('day'::text, created_at) AS date,
    count(*) AS total_searches,
    count(DISTINCT user_id) AS unique_users,
    avg(results_count) AS avg_results_count,
    avg(response_time_ms) AS avg_response_time_ms,
    mode() WITHIN GROUP (ORDER BY query) AS most_common_query
   FROM dev.mcp_search_history
  GROUP BY (date_trunc('day'::text, created_at))
  ORDER BY (date_trunc('day'::text, created_at)) DESC;


--
-- Name: mcp_search_history_id_seq; Type: SEQUENCE; Schema: dev; Owner: -
--

CREATE SEQUENCE dev.mcp_search_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: mcp_search_history_id_seq; Type: SEQUENCE OWNED BY; Schema: dev; Owner: -
--

ALTER SEQUENCE dev.mcp_search_history_id_seq OWNED BY dev.mcp_search_history.id;


--
-- Name: mcp_tools; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.mcp_tools (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    category character varying(100),
    input_schema jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    last_used timestamp with time zone,
    call_count integer DEFAULT 0,
    avg_response_time integer DEFAULT 0,
    success_rate numeric(5,2) DEFAULT 100.0,
    is_active boolean DEFAULT true
);


--
-- Name: mcp_tools_id_seq; Type: SEQUENCE; Schema: dev; Owner: -
--

CREATE SEQUENCE dev.mcp_tools_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: mcp_tools_id_seq; Type: SEQUENCE OWNED BY; Schema: dev; Owner: -
--

ALTER SEQUENCE dev.mcp_tools_id_seq OWNED BY dev.mcp_tools.id;


--
-- Name: mcp_unified_search_embeddings; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.mcp_unified_search_embeddings (
    id integer NOT NULL,
    item_name text NOT NULL,
    item_type text NOT NULL,
    category text NOT NULL,
    description text,
    embedding public.vector(1536),
    keywords text[],
    metadata jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT mcp_unified_search_embeddings_item_type_check CHECK ((item_type = ANY (ARRAY['tool'::text, 'prompt'::text, 'resource'::text])))
);


--
-- Name: mcp_unified_search_embeddings_id_seq; Type: SEQUENCE; Schema: dev; Owner: -
--

CREATE SEQUENCE dev.mcp_unified_search_embeddings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: mcp_unified_search_embeddings_id_seq; Type: SEQUENCE OWNED BY; Schema: dev; Owner: -
--

ALTER SEQUENCE dev.mcp_unified_search_embeddings_id_seq OWNED BY dev.mcp_unified_search_embeddings.id;


--
-- Name: memory_associations; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.memory_associations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id character varying(255),
    source_memory_type character varying(20) NOT NULL,
    source_memory_id uuid NOT NULL,
    target_memory_type character varying(20) NOT NULL,
    target_memory_id uuid NOT NULL,
    association_type character varying(50) NOT NULL,
    strength double precision DEFAULT 0.5,
    context text,
    auto_discovered boolean DEFAULT false,
    confirmation_count integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT memory_associations_source_memory_type_check CHECK (((source_memory_type)::text = ANY ((ARRAY['factual'::character varying, 'procedural'::character varying, 'episodic'::character varying, 'semantic'::character varying, 'working'::character varying])::text[]))),
    CONSTRAINT memory_associations_strength_check CHECK (((strength >= (0)::double precision) AND (strength <= (1)::double precision))),
    CONSTRAINT memory_associations_target_memory_type_check CHECK (((target_memory_type)::text = ANY ((ARRAY['factual'::character varying, 'procedural'::character varying, 'episodic'::character varying, 'semantic'::character varying, 'working'::character varying])::text[])))
);


--
-- Name: memory_config; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.memory_config (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id character varying(255),
    max_factual_memories integer DEFAULT 10000,
    max_procedural_memories integer DEFAULT 1000,
    default_similarity_threshold double precision DEFAULT 0.7,
    enable_auto_learning boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: memory_extraction_logs; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.memory_extraction_logs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id character varying(255),
    extraction_session_id uuid NOT NULL,
    source_content_hash character varying(64),
    extracted_memories jsonb NOT NULL,
    extraction_method character varying(50) NOT NULL,
    confidence_score double precision,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: memory_metadata; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.memory_metadata (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id character varying(255),
    memory_type character varying(20) NOT NULL,
    memory_id uuid NOT NULL,
    access_count integer DEFAULT 0,
    last_accessed_at timestamp with time zone,
    first_accessed_at timestamp with time zone DEFAULT now(),
    modification_count integer DEFAULT 0,
    last_modified_at timestamp with time zone,
    version integer DEFAULT 1,
    accuracy_score double precision,
    relevance_score double precision,
    completeness_score double precision,
    user_rating integer,
    user_feedback text,
    feedback_timestamp timestamp with time zone,
    system_flags jsonb DEFAULT '{}'::jsonb,
    priority_level integer DEFAULT 3,
    dependency_count integer DEFAULT 0,
    reference_count integer DEFAULT 0,
    lifecycle_stage character varying(20) DEFAULT 'active'::character varying,
    auto_expire boolean DEFAULT false,
    expire_after_days integer,
    reinforcement_score double precision DEFAULT 0.0,
    learning_curve jsonb DEFAULT '[]'::jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT memory_metadata_accuracy_score_check CHECK (((accuracy_score >= (0)::double precision) AND (accuracy_score <= (1)::double precision))),
    CONSTRAINT memory_metadata_completeness_score_check CHECK (((completeness_score >= (0)::double precision) AND (completeness_score <= (1)::double precision))),
    CONSTRAINT memory_metadata_lifecycle_stage_check CHECK (((lifecycle_stage)::text = ANY ((ARRAY['active'::character varying, 'stale'::character varying, 'deprecated'::character varying, 'archived'::character varying])::text[]))),
    CONSTRAINT memory_metadata_memory_type_check CHECK (((memory_type)::text = ANY ((ARRAY['factual'::character varying, 'procedural'::character varying, 'episodic'::character varying, 'semantic'::character varying, 'working'::character varying])::text[]))),
    CONSTRAINT memory_metadata_priority_level_check CHECK (((priority_level >= 1) AND (priority_level <= 5))),
    CONSTRAINT memory_metadata_relevance_score_check CHECK (((relevance_score >= (0)::double precision) AND (relevance_score <= (1)::double precision))),
    CONSTRAINT memory_metadata_user_rating_check CHECK (((user_rating >= 1) AND (user_rating <= 5)))
);


--
-- Name: memory_statistics; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.memory_statistics (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id character varying(255),
    period_type character varying(20) NOT NULL,
    period_start timestamp with time zone NOT NULL,
    period_end timestamp with time zone NOT NULL,
    factual_count integer DEFAULT 0,
    procedural_count integer DEFAULT 0,
    episodic_count integer DEFAULT 0,
    semantic_count integer DEFAULT 0,
    working_count integer DEFAULT 0,
    total_accesses integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT memory_statistics_period_type_check CHECK (((period_type)::text = ANY ((ARRAY['daily'::character varying, 'weekly'::character varying, 'monthly'::character varying, 'yearly'::character varying])::text[])))
);


--
-- Name: model_capabilities; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.model_capabilities (
    model_id text NOT NULL,
    capability text NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: model_embeddings; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.model_embeddings (
    id bigint NOT NULL,
    model_id text,
    provider text NOT NULL,
    description text NOT NULL,
    embedding jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: model_embeddings_id_seq; Type: SEQUENCE; Schema: dev; Owner: -
--

CREATE SEQUENCE dev.model_embeddings_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: model_embeddings_id_seq; Type: SEQUENCE OWNED BY; Schema: dev; Owner: -
--

ALTER SEQUENCE dev.model_embeddings_id_seq OWNED BY dev.model_embeddings.id;


--
-- Name: model_statistics; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.model_statistics (
    id bigint NOT NULL,
    model_id text NOT NULL,
    provider text NOT NULL,
    service_type text NOT NULL,
    operation_type text NOT NULL,
    date date DEFAULT CURRENT_DATE NOT NULL,
    total_requests integer DEFAULT 0,
    total_input_tokens bigint DEFAULT 0,
    total_output_tokens bigint DEFAULT 0,
    total_tokens bigint DEFAULT 0,
    total_input_units numeric DEFAULT 0,
    total_output_units numeric DEFAULT 0,
    total_cost_usd numeric(12,8) DEFAULT 0,
    last_updated timestamp with time zone DEFAULT now(),
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: model_statistics_id_seq; Type: SEQUENCE; Schema: dev; Owner: -
--

CREATE SEQUENCE dev.model_statistics_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: model_statistics_id_seq; Type: SEQUENCE OWNED BY; Schema: dev; Owner: -
--

ALTER SEQUENCE dev.model_statistics_id_seq OWNED BY dev.model_statistics.id;


--
-- Name: models; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.models (
    model_id text NOT NULL,
    model_type text NOT NULL,
    provider text NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: orders; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.orders (
    id integer NOT NULL,
    order_id character varying(255) NOT NULL,
    user_id character varying(255),
    shopify_order_id character varying(255),
    order_data jsonb DEFAULT '{}'::jsonb,
    total_amount numeric(10,2) NOT NULL,
    currency character varying(3) DEFAULT 'USD'::character varying,
    status character varying(50) DEFAULT 'pending'::character varying,
    payment_status character varying(50) DEFAULT 'unpaid'::character varying,
    fulfillment_status character varying(50) DEFAULT 'unfulfilled'::character varying,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: orders_id_seq; Type: SEQUENCE; Schema: dev; Owner: -
--

CREATE SEQUENCE dev.orders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: orders_id_seq; Type: SEQUENCE OWNED BY; Schema: dev; Owner: -
--

ALTER SEQUENCE dev.orders_id_seq OWNED BY dev.orders.id;


--
-- Name: procedural_memories; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.procedural_memories (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id character varying(255),
    procedure_name character varying(200) NOT NULL,
    domain character varying(100) NOT NULL,
    trigger_conditions jsonb NOT NULL,
    steps jsonb NOT NULL,
    expected_outcome text,
    success_rate double precision DEFAULT 0.0,
    usage_count integer DEFAULT 0,
    last_used_at timestamp with time zone,
    embedding public.vector(1536),
    difficulty_level integer,
    estimated_time_minutes integer,
    required_tools jsonb DEFAULT '[]'::jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT procedural_memories_difficulty_level_check CHECK (((difficulty_level >= 1) AND (difficulty_level <= 5)))
);


--
-- Name: prompt_embeddings; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.prompt_embeddings (
    id bigint NOT NULL,
    prompt_name text NOT NULL,
    description text,
    embedding jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: prompt_embeddings_id_seq; Type: SEQUENCE; Schema: dev; Owner: -
--

CREATE SEQUENCE dev.prompt_embeddings_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: prompt_embeddings_id_seq; Type: SEQUENCE OWNED BY; Schema: dev; Owner: -
--

ALTER SEQUENCE dev.prompt_embeddings_id_seq OWNED BY dev.prompt_embeddings.id;


--
-- Name: resource_embeddings; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.resource_embeddings (
    id bigint NOT NULL,
    resource_uri text NOT NULL,
    category text,
    name text,
    description text,
    embedding jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: resource_embeddings_id_seq; Type: SEQUENCE; Schema: dev; Owner: -
--

CREATE SEQUENCE dev.resource_embeddings_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: resource_embeddings_id_seq; Type: SEQUENCE OWNED BY; Schema: dev; Owner: -
--

ALTER SEQUENCE dev.resource_embeddings_id_seq OWNED BY dev.resource_embeddings.id;


--
-- Name: semantic_memories; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.semantic_memories (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id character varying(255),
    concept_name character varying(200) NOT NULL,
    concept_category character varying(100) NOT NULL,
    definition text NOT NULL,
    properties jsonb DEFAULT '{}'::jsonb,
    related_concepts jsonb DEFAULT '[]'::jsonb,
    hierarchical_level integer DEFAULT 0,
    parent_concept_id uuid,
    use_cases jsonb DEFAULT '[]'::jsonb,
    examples jsonb DEFAULT '[]'::jsonb,
    embedding public.vector(1536),
    mastery_level double precision DEFAULT 0.5,
    learning_source character varying(100),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT semantic_memories_mastery_level_check CHECK (((mastery_level >= (0)::double precision) AND (mastery_level <= (1)::double precision)))
);


--
-- Name: session_memories; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.session_memories (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    session_id character varying(64) NOT NULL,
    user_id uuid,
    conversation_summary text,
    user_context jsonb DEFAULT '{}'::jsonb,
    key_decisions jsonb DEFAULT '[]'::jsonb,
    ongoing_tasks jsonb DEFAULT '[]'::jsonb,
    user_preferences jsonb DEFAULT '{}'::jsonb,
    important_facts jsonb DEFAULT '[]'::jsonb,
    total_messages integer DEFAULT 0,
    messages_since_last_summary integer DEFAULT 0,
    last_summary_at timestamp with time zone,
    is_active boolean DEFAULT true,
    session_metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: session_messages; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.session_messages (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    session_id character varying(64) NOT NULL,
    user_id uuid,
    message_type character varying(20) NOT NULL,
    role character varying(20) NOT NULL,
    content text NOT NULL,
    tool_calls jsonb,
    tool_call_id character varying(100),
    message_metadata jsonb DEFAULT '{}'::jsonb,
    tokens_used integer DEFAULT 0,
    cost_usd numeric(10,8) DEFAULT 0,
    is_summary_candidate boolean DEFAULT true,
    importance_score double precision DEFAULT 0.5,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: sessions; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.sessions (
    id integer NOT NULL,
    session_id character varying(255) NOT NULL,
    user_id character varying(255),
    conversation_data jsonb DEFAULT '{}'::jsonb,
    status character varying(50) DEFAULT 'active'::character varying,
    created_at timestamp with time zone DEFAULT now(),
    expires_at timestamp with time zone,
    updated_at timestamp with time zone DEFAULT now(),
    last_activity timestamp with time zone DEFAULT now(),
    is_active boolean DEFAULT true,
    message_count integer DEFAULT 0,
    total_tokens integer DEFAULT 0,
    total_cost numeric(10,6) DEFAULT 0.0,
    metadata jsonb DEFAULT '{}'::jsonb,
    session_summary text DEFAULT ''::text
);


--
-- Name: sessions_id_seq; Type: SEQUENCE; Schema: dev; Owner: -
--

CREATE SEQUENCE dev.sessions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: dev; Owner: -
--

ALTER SEQUENCE dev.sessions_id_seq OWNED BY dev.sessions.id;


--
-- Name: span_logs; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.span_logs (
    id integer NOT NULL,
    span_id character varying(255),
    "timestamp" timestamp with time zone DEFAULT now(),
    level character varying(20),
    message text,
    fields jsonb DEFAULT '{}'::jsonb
);


--
-- Name: span_logs_id_seq; Type: SEQUENCE; Schema: dev; Owner: -
--

CREATE SEQUENCE dev.span_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: span_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: dev; Owner: -
--

ALTER SEQUENCE dev.span_logs_id_seq OWNED BY dev.span_logs.id;


--
-- Name: spans; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.spans (
    span_id character varying(255) NOT NULL,
    trace_id character varying(255),
    parent_span_id character varying(255),
    operation_name character varying(255),
    start_time timestamp with time zone DEFAULT now(),
    end_time timestamp with time zone,
    duration double precision,
    tags jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now(),
    status text DEFAULT 'running'::text,
    error_message text,
    CONSTRAINT spans_status_check CHECK ((status = ANY (ARRAY['running'::text, 'completed'::text, 'failed'::text])))
);


--
-- Name: subscriptions; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.subscriptions (
    id integer NOT NULL,
    user_id character varying(255),
    subscription_scope character varying(50) NOT NULL,
    app_id character varying(255),
    stripe_subscription_id character varying(255),
    stripe_customer_id character varying(255),
    status character varying(50) DEFAULT 'inactive'::character varying,
    plan_type character varying(50) DEFAULT 'free'::character varying,
    credits_included integer DEFAULT 0,
    current_period_start timestamp with time zone,
    current_period_end timestamp with time zone,
    canceled_at timestamp with time zone,
    downgrade_at_period_end boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: subscriptions_id_seq; Type: SEQUENCE; Schema: dev; Owner: -
--

CREATE SEQUENCE dev.subscriptions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: subscriptions_id_seq; Type: SEQUENCE OWNED BY; Schema: dev; Owner: -
--

ALTER SEQUENCE dev.subscriptions_id_seq OWNED BY dev.subscriptions.id;


--
-- Name: tool_embeddings; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.tool_embeddings (
    id bigint NOT NULL,
    tool_name text NOT NULL,
    description text,
    embedding jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: tool_embeddings_id_seq; Type: SEQUENCE; Schema: dev; Owner: -
--

CREATE SEQUENCE dev.tool_embeddings_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tool_embeddings_id_seq; Type: SEQUENCE OWNED BY; Schema: dev; Owner: -
--

ALTER SEQUENCE dev.tool_embeddings_id_seq OWNED BY dev.tool_embeddings.id;


--
-- Name: traces; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.traces (
    trace_id character varying(255) NOT NULL,
    user_id character varying(255),
    session_id character varying(255),
    operation_name character varying(255),
    start_time timestamp with time zone DEFAULT now(),
    end_time timestamp with time zone,
    duration double precision,
    status character varying(50),
    tags jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now(),
    service_name text DEFAULT 'agent-service'::text NOT NULL,
    total_spans integer DEFAULT 0,
    error_message text
);


--
-- Name: user_credit_transactions; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.user_credit_transactions (
    id bigint NOT NULL,
    user_id character varying NOT NULL,
    transaction_type character varying NOT NULL,
    credits_amount numeric(10,3) NOT NULL,
    credits_before numeric(10,3) NOT NULL,
    credits_after numeric(10,3) NOT NULL,
    usage_record_id bigint,
    description text,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: user_credit_transactions_id_seq; Type: SEQUENCE; Schema: dev; Owner: -
--

CREATE SEQUENCE dev.user_credit_transactions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_credit_transactions_id_seq; Type: SEQUENCE OWNED BY; Schema: dev; Owner: -
--

ALTER SEQUENCE dev.user_credit_transactions_id_seq OWNED BY dev.user_credit_transactions.id;


--
-- Name: user_knowledge; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.user_knowledge (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id text NOT NULL,
    text text NOT NULL,
    embedding_vector public.vector(1536),
    metadata jsonb DEFAULT '{}'::jsonb,
    chunk_index integer DEFAULT 0,
    source_document text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: user_tasks; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.user_tasks (
    id integer NOT NULL,
    task_id uuid DEFAULT extensions.uuid_generate_v4(),
    user_id character varying(255),
    task_type character varying(100) NOT NULL,
    description text,
    config jsonb,
    callback_url character varying(500),
    status character varying(50) DEFAULT 'active'::character varying,
    last_check timestamp with time zone,
    next_check timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: user_tasks_id_seq; Type: SEQUENCE; Schema: dev; Owner: -
--

CREATE SEQUENCE dev.user_tasks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_tasks_id_seq; Type: SEQUENCE OWNED BY; Schema: dev; Owner: -
--

ALTER SEQUENCE dev.user_tasks_id_seq OWNED BY dev.user_tasks.id;


--
-- Name: user_usage_records; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.user_usage_records (
    id bigint NOT NULL,
    user_id character varying NOT NULL,
    session_id character varying,
    trace_id character varying,
    endpoint character varying NOT NULL,
    event_type character varying NOT NULL,
    credits_charged numeric(10,3) DEFAULT 0 NOT NULL,
    cost_usd numeric(10,6) DEFAULT 0 NOT NULL,
    calculation_method character varying DEFAULT 'unknown'::character varying,
    tokens_used integer DEFAULT 0,
    prompt_tokens integer DEFAULT 0,
    completion_tokens integer DEFAULT 0,
    model_name character varying,
    provider character varying,
    tool_name character varying,
    operation_name character varying,
    billing_metadata jsonb DEFAULT '{}'::jsonb,
    request_data jsonb DEFAULT '{}'::jsonb,
    response_data jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: user_usage_records_id_seq; Type: SEQUENCE; Schema: dev; Owner: -
--

CREATE SEQUENCE dev.user_usage_records_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_usage_records_id_seq; Type: SEQUENCE OWNED BY; Schema: dev; Owner: -
--

ALTER SEQUENCE dev.user_usage_records_id_seq OWNED BY dev.user_usage_records.id;


--
-- Name: users; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.users (
    id integer NOT NULL,
    user_id character varying(255) NOT NULL,
    auth0_id character varying(255),
    email character varying(255),
    phone character varying(50),
    name character varying(255),
    credits_remaining numeric(10,3) DEFAULT 1000,
    credits_total numeric(10,3) DEFAULT 1000,
    subscription_status character varying(50) DEFAULT 'free'::character varying,
    is_active boolean DEFAULT true,
    shipping_addresses jsonb DEFAULT '[]'::jsonb,
    payment_methods jsonb DEFAULT '[]'::jsonb,
    preferences jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: dev; Owner: -
--

CREATE SEQUENCE dev.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: dev; Owner: -
--

ALTER SEQUENCE dev.users_id_seq OWNED BY dev.users.id;


--
-- Name: working_memories; Type: TABLE; Schema: dev; Owner: -
--

CREATE TABLE dev.working_memories (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id character varying(255),
    context_type character varying(50) NOT NULL,
    context_id character varying(200) NOT NULL,
    state_data jsonb NOT NULL,
    current_step character varying(200),
    progress_percentage double precision DEFAULT 0.0,
    next_actions jsonb DEFAULT '[]'::jsonb,
    dependencies jsonb DEFAULT '[]'::jsonb,
    blocking_issues jsonb DEFAULT '[]'::jsonb,
    embedding public.vector(1536),
    priority integer DEFAULT 3,
    expires_at timestamp with time zone DEFAULT (now() + '24:00:00'::interval),
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT working_memories_priority_check CHECK (((priority >= 1) AND (priority <= 5))),
    CONSTRAINT working_memories_progress_percentage_check CHECK (((progress_percentage >= (0)::double precision) AND (progress_percentage <= (100)::double precision)))
);


--
-- Name: carts id; Type: DEFAULT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.carts ALTER COLUMN id SET DEFAULT nextval('dev.carts_id_seq'::regclass);


--
-- Name: events id; Type: DEFAULT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.events ALTER COLUMN id SET DEFAULT nextval('dev.events_id_seq'::regclass);


--
-- Name: langgraph_executions id; Type: DEFAULT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.langgraph_executions ALTER COLUMN id SET DEFAULT nextval('dev.langgraph_executions_id_seq'::regclass);


--
-- Name: mcp_prompts id; Type: DEFAULT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.mcp_prompts ALTER COLUMN id SET DEFAULT nextval('dev.mcp_prompts_id_seq'::regclass);


--
-- Name: mcp_resources id; Type: DEFAULT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.mcp_resources ALTER COLUMN id SET DEFAULT nextval('dev.mcp_resources_id_seq'::regclass);


--
-- Name: mcp_search_history id; Type: DEFAULT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.mcp_search_history ALTER COLUMN id SET DEFAULT nextval('dev.mcp_search_history_id_seq'::regclass);


--
-- Name: mcp_tools id; Type: DEFAULT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.mcp_tools ALTER COLUMN id SET DEFAULT nextval('dev.mcp_tools_id_seq'::regclass);


--
-- Name: mcp_unified_search_embeddings id; Type: DEFAULT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.mcp_unified_search_embeddings ALTER COLUMN id SET DEFAULT nextval('dev.mcp_unified_search_embeddings_id_seq'::regclass);


--
-- Name: model_embeddings id; Type: DEFAULT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.model_embeddings ALTER COLUMN id SET DEFAULT nextval('dev.model_embeddings_id_seq'::regclass);


--
-- Name: model_statistics id; Type: DEFAULT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.model_statistics ALTER COLUMN id SET DEFAULT nextval('dev.model_statistics_id_seq'::regclass);


--
-- Name: orders id; Type: DEFAULT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.orders ALTER COLUMN id SET DEFAULT nextval('dev.orders_id_seq'::regclass);


--
-- Name: prompt_embeddings id; Type: DEFAULT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.prompt_embeddings ALTER COLUMN id SET DEFAULT nextval('dev.prompt_embeddings_id_seq'::regclass);


--
-- Name: resource_embeddings id; Type: DEFAULT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.resource_embeddings ALTER COLUMN id SET DEFAULT nextval('dev.resource_embeddings_id_seq'::regclass);


--
-- Name: sessions id; Type: DEFAULT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.sessions ALTER COLUMN id SET DEFAULT nextval('dev.sessions_id_seq'::regclass);


--
-- Name: span_logs id; Type: DEFAULT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.span_logs ALTER COLUMN id SET DEFAULT nextval('dev.span_logs_id_seq'::regclass);


--
-- Name: subscriptions id; Type: DEFAULT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.subscriptions ALTER COLUMN id SET DEFAULT nextval('dev.subscriptions_id_seq'::regclass);


--
-- Name: tool_embeddings id; Type: DEFAULT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.tool_embeddings ALTER COLUMN id SET DEFAULT nextval('dev.tool_embeddings_id_seq'::regclass);


--
-- Name: user_credit_transactions id; Type: DEFAULT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.user_credit_transactions ALTER COLUMN id SET DEFAULT nextval('dev.user_credit_transactions_id_seq'::regclass);


--
-- Name: user_tasks id; Type: DEFAULT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.user_tasks ALTER COLUMN id SET DEFAULT nextval('dev.user_tasks_id_seq'::regclass);


--
-- Name: user_usage_records id; Type: DEFAULT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.user_usage_records ALTER COLUMN id SET DEFAULT nextval('dev.user_usage_records_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.users ALTER COLUMN id SET DEFAULT nextval('dev.users_id_seq'::regclass);


--
-- Name: carts carts_cart_id_key; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.carts
    ADD CONSTRAINT carts_cart_id_key UNIQUE (cart_id);


--
-- Name: carts carts_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.carts
    ADD CONSTRAINT carts_pkey PRIMARY KEY (id);


--
-- Name: checkpoint_blobs checkpoint_blobs_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.checkpoint_blobs
    ADD CONSTRAINT checkpoint_blobs_pkey PRIMARY KEY (thread_id, checkpoint_ns, channel, version);


--
-- Name: checkpoint_migrations checkpoint_migrations_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.checkpoint_migrations
    ADD CONSTRAINT checkpoint_migrations_pkey PRIMARY KEY (v);


--
-- Name: checkpoint_writes checkpoint_writes_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.checkpoint_writes
    ADD CONSTRAINT checkpoint_writes_pkey PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx);


--
-- Name: checkpoints checkpoints_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.checkpoints
    ADD CONSTRAINT checkpoints_pkey PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id);


--
-- Name: db_meta_embedding db_meta_embedding_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.db_meta_embedding
    ADD CONSTRAINT db_meta_embedding_pkey PRIMARY KEY (id);


--
-- Name: episodic_memories episodic_memories_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.episodic_memories
    ADD CONSTRAINT episodic_memories_pkey PRIMARY KEY (id);


--
-- Name: events events_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.events
    ADD CONSTRAINT events_pkey PRIMARY KEY (id);


--
-- Name: factual_memories factual_memories_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.factual_memories
    ADD CONSTRAINT factual_memories_pkey PRIMARY KEY (id);


--
-- Name: factual_memories factual_memories_user_id_fact_type_subject_predicate_key; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.factual_memories
    ADD CONSTRAINT factual_memories_user_id_fact_type_subject_predicate_key UNIQUE (user_id, fact_type, subject, predicate);


--
-- Name: langgraph_executions langgraph_executions_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.langgraph_executions
    ADD CONSTRAINT langgraph_executions_pkey PRIMARY KEY (id);


--
-- Name: mcp_prompts mcp_prompts_name_key; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.mcp_prompts
    ADD CONSTRAINT mcp_prompts_name_key UNIQUE (name);


--
-- Name: mcp_prompts mcp_prompts_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.mcp_prompts
    ADD CONSTRAINT mcp_prompts_pkey PRIMARY KEY (id);


--
-- Name: mcp_resources mcp_resources_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.mcp_resources
    ADD CONSTRAINT mcp_resources_pkey PRIMARY KEY (id);


--
-- Name: mcp_resources mcp_resources_uri_key; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.mcp_resources
    ADD CONSTRAINT mcp_resources_uri_key UNIQUE (uri);


--
-- Name: mcp_search_history mcp_search_history_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.mcp_search_history
    ADD CONSTRAINT mcp_search_history_pkey PRIMARY KEY (id);


--
-- Name: mcp_tools mcp_tools_name_key; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.mcp_tools
    ADD CONSTRAINT mcp_tools_name_key UNIQUE (name);


--
-- Name: mcp_tools mcp_tools_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.mcp_tools
    ADD CONSTRAINT mcp_tools_pkey PRIMARY KEY (id);


--
-- Name: mcp_unified_search_embeddings mcp_unified_search_embeddings_item_name_key; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.mcp_unified_search_embeddings
    ADD CONSTRAINT mcp_unified_search_embeddings_item_name_key UNIQUE (item_name);


--
-- Name: mcp_unified_search_embeddings mcp_unified_search_embeddings_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.mcp_unified_search_embeddings
    ADD CONSTRAINT mcp_unified_search_embeddings_pkey PRIMARY KEY (id);


--
-- Name: memory_associations memory_associations_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.memory_associations
    ADD CONSTRAINT memory_associations_pkey PRIMARY KEY (id);


--
-- Name: memory_associations memory_associations_user_id_source_memory_type_source_memor_key; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.memory_associations
    ADD CONSTRAINT memory_associations_user_id_source_memory_type_source_memor_key UNIQUE (user_id, source_memory_type, source_memory_id, target_memory_type, target_memory_id, association_type);


--
-- Name: memory_config memory_config_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.memory_config
    ADD CONSTRAINT memory_config_pkey PRIMARY KEY (id);


--
-- Name: memory_config memory_config_user_id_key; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.memory_config
    ADD CONSTRAINT memory_config_user_id_key UNIQUE (user_id);


--
-- Name: memory_extraction_logs memory_extraction_logs_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.memory_extraction_logs
    ADD CONSTRAINT memory_extraction_logs_pkey PRIMARY KEY (id);


--
-- Name: memory_metadata memory_metadata_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.memory_metadata
    ADD CONSTRAINT memory_metadata_pkey PRIMARY KEY (id);


--
-- Name: memory_metadata memory_metadata_user_id_memory_type_memory_id_key; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.memory_metadata
    ADD CONSTRAINT memory_metadata_user_id_memory_type_memory_id_key UNIQUE (user_id, memory_type, memory_id);


--
-- Name: memory_statistics memory_statistics_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.memory_statistics
    ADD CONSTRAINT memory_statistics_pkey PRIMARY KEY (id);


--
-- Name: memory_statistics memory_statistics_user_id_period_type_period_start_key; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.memory_statistics
    ADD CONSTRAINT memory_statistics_user_id_period_type_period_start_key UNIQUE (user_id, period_type, period_start);


--
-- Name: model_capabilities model_capabilities_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.model_capabilities
    ADD CONSTRAINT model_capabilities_pkey PRIMARY KEY (model_id, capability);


--
-- Name: model_embeddings model_embeddings_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.model_embeddings
    ADD CONSTRAINT model_embeddings_pkey PRIMARY KEY (id);


--
-- Name: model_statistics model_statistics_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.model_statistics
    ADD CONSTRAINT model_statistics_pkey PRIMARY KEY (id);


--
-- Name: models models_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.models
    ADD CONSTRAINT models_pkey PRIMARY KEY (model_id);


--
-- Name: orders orders_order_id_key; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.orders
    ADD CONSTRAINT orders_order_id_key UNIQUE (order_id);


--
-- Name: orders orders_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.orders
    ADD CONSTRAINT orders_pkey PRIMARY KEY (id);


--
-- Name: procedural_memories procedural_memories_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.procedural_memories
    ADD CONSTRAINT procedural_memories_pkey PRIMARY KEY (id);


--
-- Name: procedural_memories procedural_memories_user_id_procedure_name_domain_key; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.procedural_memories
    ADD CONSTRAINT procedural_memories_user_id_procedure_name_domain_key UNIQUE (user_id, procedure_name, domain);


--
-- Name: prompt_embeddings prompt_embeddings_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.prompt_embeddings
    ADD CONSTRAINT prompt_embeddings_pkey PRIMARY KEY (id);


--
-- Name: prompt_embeddings prompt_embeddings_prompt_name_key; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.prompt_embeddings
    ADD CONSTRAINT prompt_embeddings_prompt_name_key UNIQUE (prompt_name);


--
-- Name: resource_embeddings resource_embeddings_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.resource_embeddings
    ADD CONSTRAINT resource_embeddings_pkey PRIMARY KEY (id);


--
-- Name: resource_embeddings resource_embeddings_resource_uri_key; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.resource_embeddings
    ADD CONSTRAINT resource_embeddings_resource_uri_key UNIQUE (resource_uri);


--
-- Name: semantic_memories semantic_memories_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.semantic_memories
    ADD CONSTRAINT semantic_memories_pkey PRIMARY KEY (id);


--
-- Name: semantic_memories semantic_memories_user_id_concept_name_concept_category_key; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.semantic_memories
    ADD CONSTRAINT semantic_memories_user_id_concept_name_concept_category_key UNIQUE (user_id, concept_name, concept_category);


--
-- Name: session_memories session_memories_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.session_memories
    ADD CONSTRAINT session_memories_pkey PRIMARY KEY (id);


--
-- Name: session_memories session_memories_session_id_key; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.session_memories
    ADD CONSTRAINT session_memories_session_id_key UNIQUE (session_id);


--
-- Name: session_messages session_messages_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.session_messages
    ADD CONSTRAINT session_messages_pkey PRIMARY KEY (id);


--
-- Name: sessions sessions_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.sessions
    ADD CONSTRAINT sessions_pkey PRIMARY KEY (id);


--
-- Name: sessions sessions_session_id_key; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.sessions
    ADD CONSTRAINT sessions_session_id_key UNIQUE (session_id);


--
-- Name: span_logs span_logs_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.span_logs
    ADD CONSTRAINT span_logs_pkey PRIMARY KEY (id);


--
-- Name: spans spans_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.spans
    ADD CONSTRAINT spans_pkey PRIMARY KEY (span_id);


--
-- Name: subscriptions subscriptions_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.subscriptions
    ADD CONSTRAINT subscriptions_pkey PRIMARY KEY (id);


--
-- Name: tool_embeddings tool_embeddings_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.tool_embeddings
    ADD CONSTRAINT tool_embeddings_pkey PRIMARY KEY (id);


--
-- Name: tool_embeddings tool_embeddings_tool_name_key; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.tool_embeddings
    ADD CONSTRAINT tool_embeddings_tool_name_key UNIQUE (tool_name);


--
-- Name: traces traces_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.traces
    ADD CONSTRAINT traces_pkey PRIMARY KEY (trace_id);


--
-- Name: model_statistics unique_model_daily_stats; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.model_statistics
    ADD CONSTRAINT unique_model_daily_stats UNIQUE (model_id, provider, service_type, operation_type, date);


--
-- Name: user_credit_transactions user_credit_transactions_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.user_credit_transactions
    ADD CONSTRAINT user_credit_transactions_pkey PRIMARY KEY (id);


--
-- Name: user_knowledge user_knowledge_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.user_knowledge
    ADD CONSTRAINT user_knowledge_pkey PRIMARY KEY (id);


--
-- Name: user_tasks user_tasks_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.user_tasks
    ADD CONSTRAINT user_tasks_pkey PRIMARY KEY (id);


--
-- Name: user_tasks user_tasks_task_id_unique; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.user_tasks
    ADD CONSTRAINT user_tasks_task_id_unique UNIQUE (task_id);


--
-- Name: user_usage_records user_usage_records_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.user_usage_records
    ADD CONSTRAINT user_usage_records_pkey PRIMARY KEY (id);


--
-- Name: users users_auth0_id_key; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.users
    ADD CONSTRAINT users_auth0_id_key UNIQUE (auth0_id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_user_id_key; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.users
    ADD CONSTRAINT users_user_id_key UNIQUE (user_id);


--
-- Name: working_memories working_memories_pkey; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.working_memories
    ADD CONSTRAINT working_memories_pkey PRIMARY KEY (id);


--
-- Name: working_memories working_memories_user_id_context_type_context_id_key; Type: CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.working_memories
    ADD CONSTRAINT working_memories_user_id_context_type_context_id_key UNIQUE (user_id, context_type, context_id);


--
-- Name: checkpoint_blobs_thread_id_idx; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX checkpoint_blobs_thread_id_idx ON dev.checkpoint_blobs USING btree (thread_id);


--
-- Name: checkpoint_writes_thread_id_idx; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX checkpoint_writes_thread_id_idx ON dev.checkpoint_writes USING btree (thread_id);


--
-- Name: checkpoints_thread_id_idx; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX checkpoints_thread_id_idx ON dev.checkpoints USING btree (thread_id);


--
-- Name: db_meta_embedding_confidence_idx; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX db_meta_embedding_confidence_idx ON dev.db_meta_embedding USING btree (confidence_score);


--
-- Name: db_meta_embedding_created_at_idx; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX db_meta_embedding_created_at_idx ON dev.db_meta_embedding USING btree (created_at);


--
-- Name: db_meta_embedding_entity_name_idx; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX db_meta_embedding_entity_name_idx ON dev.db_meta_embedding USING btree (entity_name);


--
-- Name: db_meta_embedding_entity_type_idx; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX db_meta_embedding_entity_type_idx ON dev.db_meta_embedding USING btree (entity_type);


--
-- Name: db_meta_embedding_source_idx; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX db_meta_embedding_source_idx ON dev.db_meta_embedding USING btree (database_source);


--
-- Name: db_meta_embedding_vector_idx; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX db_meta_embedding_vector_idx ON dev.db_meta_embedding USING ivfflat (embedding public.vector_cosine_ops) WITH (lists='100');


--
-- Name: idx_associations_source; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_associations_source ON dev.memory_associations USING btree (source_memory_type, source_memory_id);


--
-- Name: idx_associations_strength; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_associations_strength ON dev.memory_associations USING btree (strength DESC);


--
-- Name: idx_associations_target; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_associations_target ON dev.memory_associations USING btree (target_memory_type, target_memory_id);


--
-- Name: idx_associations_user; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_associations_user ON dev.memory_associations USING btree (user_id);


--
-- Name: idx_carts_expires_at; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_carts_expires_at ON dev.carts USING btree (expires_at);


--
-- Name: idx_carts_status; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_carts_status ON dev.carts USING btree (status);


--
-- Name: idx_carts_user_id; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_carts_user_id ON dev.carts USING btree (user_id);


--
-- Name: idx_credit_transactions_created_at; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_credit_transactions_created_at ON dev.user_credit_transactions USING btree (created_at);


--
-- Name: idx_credit_transactions_user_id; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_credit_transactions_user_id ON dev.user_credit_transactions USING btree (user_id);


--
-- Name: idx_dev_capabilities_capability; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_dev_capabilities_capability ON dev.model_capabilities USING btree (capability);


--
-- Name: idx_dev_embeddings_model_id; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_dev_embeddings_model_id ON dev.model_embeddings USING btree (model_id);


--
-- Name: idx_dev_model_stats_date; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_dev_model_stats_date ON dev.model_statistics USING btree (date);


--
-- Name: idx_dev_model_stats_model_id; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_dev_model_stats_model_id ON dev.model_statistics USING btree (model_id);


--
-- Name: idx_dev_model_stats_operation_type; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_dev_model_stats_operation_type ON dev.model_statistics USING btree (operation_type);


--
-- Name: idx_dev_model_stats_provider; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_dev_model_stats_provider ON dev.model_statistics USING btree (provider);


--
-- Name: idx_dev_model_stats_service_type; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_dev_model_stats_service_type ON dev.model_statistics USING btree (service_type);


--
-- Name: idx_dev_models_provider; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_dev_models_provider ON dev.models USING btree (provider);


--
-- Name: idx_dev_models_type; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_dev_models_type ON dev.models USING btree (model_type);


--
-- Name: idx_dev_prompt_embeddings_name; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_dev_prompt_embeddings_name ON dev.prompt_embeddings USING btree (prompt_name);


--
-- Name: idx_dev_resource_embeddings_category; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_dev_resource_embeddings_category ON dev.resource_embeddings USING btree (category);


--
-- Name: idx_dev_resource_embeddings_uri; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_dev_resource_embeddings_uri ON dev.resource_embeddings USING btree (resource_uri);


--
-- Name: idx_dev_tool_embeddings_name; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_dev_tool_embeddings_name ON dev.tool_embeddings USING btree (tool_name);


--
-- Name: idx_episodic_embedding; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_episodic_embedding ON dev.episodic_memories USING ivfflat (embedding public.vector_cosine_ops);


--
-- Name: idx_episodic_emotional; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_episodic_emotional ON dev.episodic_memories USING btree (emotional_intensity DESC);


--
-- Name: idx_episodic_location; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_episodic_location ON dev.episodic_memories USING btree (user_id, location) WHERE (location IS NOT NULL);


--
-- Name: idx_episodic_user_time; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_episodic_user_time ON dev.episodic_memories USING btree (user_id, occurred_at DESC);


--
-- Name: idx_events_created_at; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_events_created_at ON dev.events USING btree (created_at);


--
-- Name: idx_events_event_id; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_events_event_id ON dev.events USING btree (event_id);


--
-- Name: idx_events_processed; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_events_processed ON dev.events USING btree (processed);


--
-- Name: idx_events_task_id; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_events_task_id ON dev.events USING btree (task_id);


--
-- Name: idx_events_type; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_events_type ON dev.events USING btree (event_type);


--
-- Name: idx_events_user_id; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_events_user_id ON dev.events USING btree (user_id);


--
-- Name: idx_factual_embedding; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_factual_embedding ON dev.factual_memories USING ivfflat (embedding public.vector_cosine_ops);


--
-- Name: idx_factual_importance; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_factual_importance ON dev.factual_memories USING btree (importance_score DESC);


--
-- Name: idx_factual_subject; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_factual_subject ON dev.factual_memories USING btree (user_id, subject);


--
-- Name: idx_factual_user_type; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_factual_user_type ON dev.factual_memories USING btree (user_id, fact_type);


--
-- Name: idx_langgraph_node_name; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_langgraph_node_name ON dev.langgraph_executions USING btree (node_name);


--
-- Name: idx_langgraph_span_id; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_langgraph_span_id ON dev.langgraph_executions USING btree (span_id);


--
-- Name: idx_langgraph_trace_id; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_langgraph_trace_id ON dev.langgraph_executions USING btree (trace_id);


--
-- Name: idx_langgraph_user_id; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_langgraph_user_id ON dev.langgraph_executions USING btree (user_id);


--
-- Name: idx_mcp_prompts_active; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_mcp_prompts_active ON dev.mcp_prompts USING btree (is_active);


--
-- Name: idx_mcp_prompts_category; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_mcp_prompts_category ON dev.mcp_prompts USING btree (category);


--
-- Name: idx_mcp_resources_active; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_mcp_resources_active ON dev.mcp_resources USING btree (is_active);


--
-- Name: idx_mcp_resources_type; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_mcp_resources_type ON dev.mcp_resources USING btree (resource_type);


--
-- Name: idx_mcp_search_history_created; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_mcp_search_history_created ON dev.mcp_search_history USING btree (created_at);


--
-- Name: idx_mcp_search_history_query; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_mcp_search_history_query ON dev.mcp_search_history USING btree (query);


--
-- Name: idx_mcp_search_history_user; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_mcp_search_history_user ON dev.mcp_search_history USING btree (user_id);


--
-- Name: idx_mcp_tools_active; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_mcp_tools_active ON dev.mcp_tools USING btree (is_active);


--
-- Name: idx_mcp_tools_category; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_mcp_tools_category ON dev.mcp_tools USING btree (category);


--
-- Name: idx_mcp_unified_search_embeddings_category; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_mcp_unified_search_embeddings_category ON dev.mcp_unified_search_embeddings USING btree (category);


--
-- Name: idx_mcp_unified_search_embeddings_name; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_mcp_unified_search_embeddings_name ON dev.mcp_unified_search_embeddings USING btree (item_name);


--
-- Name: idx_mcp_unified_search_embeddings_type; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_mcp_unified_search_embeddings_type ON dev.mcp_unified_search_embeddings USING btree (item_type);


--
-- Name: idx_mcp_unified_search_embeddings_updated; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_mcp_unified_search_embeddings_updated ON dev.mcp_unified_search_embeddings USING btree (updated_at);


--
-- Name: idx_mcp_unified_search_embeddings_vector; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_mcp_unified_search_embeddings_vector ON dev.mcp_unified_search_embeddings USING ivfflat (embedding public.vector_cosine_ops) WITH (lists='100');


--
-- Name: idx_metadata_access; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_metadata_access ON dev.memory_metadata USING btree (access_count DESC);


--
-- Name: idx_metadata_flags; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_metadata_flags ON dev.memory_metadata USING gin (system_flags);


--
-- Name: idx_metadata_lifecycle; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_metadata_lifecycle ON dev.memory_metadata USING btree (lifecycle_stage);


--
-- Name: idx_metadata_memory; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_metadata_memory ON dev.memory_metadata USING btree (memory_type, memory_id);


--
-- Name: idx_metadata_priority; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_metadata_priority ON dev.memory_metadata USING btree (priority_level DESC);


--
-- Name: idx_metadata_quality; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_metadata_quality ON dev.memory_metadata USING btree (accuracy_score DESC, relevance_score DESC);


--
-- Name: idx_metadata_user_type; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_metadata_user_type ON dev.memory_metadata USING btree (user_id, memory_type);


--
-- Name: idx_orders_created_at; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_orders_created_at ON dev.orders USING btree (created_at);


--
-- Name: idx_orders_payment_status; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_orders_payment_status ON dev.orders USING btree (payment_status);


--
-- Name: idx_orders_shopify_order_id; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_orders_shopify_order_id ON dev.orders USING btree (shopify_order_id);


--
-- Name: idx_orders_status; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_orders_status ON dev.orders USING btree (status);


--
-- Name: idx_orders_user_id; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_orders_user_id ON dev.orders USING btree (user_id);


--
-- Name: idx_procedural_embedding; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_procedural_embedding ON dev.procedural_memories USING ivfflat (embedding public.vector_cosine_ops);


--
-- Name: idx_procedural_usage; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_procedural_usage ON dev.procedural_memories USING btree (usage_count DESC);


--
-- Name: idx_procedural_user_domain; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_procedural_user_domain ON dev.procedural_memories USING btree (user_id, domain);


--
-- Name: idx_semantic_embedding; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_semantic_embedding ON dev.semantic_memories USING ivfflat (embedding public.vector_cosine_ops);


--
-- Name: idx_semantic_hierarchy; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_semantic_hierarchy ON dev.semantic_memories USING btree (parent_concept_id) WHERE (parent_concept_id IS NOT NULL);


--
-- Name: idx_semantic_mastery; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_semantic_mastery ON dev.semantic_memories USING btree (mastery_level DESC);


--
-- Name: idx_semantic_user_category; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_semantic_user_category ON dev.semantic_memories USING btree (user_id, concept_category);


--
-- Name: idx_session_memories_active; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_session_memories_active ON dev.session_memories USING btree (is_active, updated_at) WHERE (is_active = true);


--
-- Name: idx_session_memories_user; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_session_memories_user ON dev.session_memories USING btree (user_id);


--
-- Name: idx_session_messages_session; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_session_messages_session ON dev.session_messages USING btree (session_id);


--
-- Name: idx_session_messages_time; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_session_messages_time ON dev.session_messages USING btree (created_at DESC);


--
-- Name: idx_session_messages_type; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_session_messages_type ON dev.session_messages USING btree (message_type);


--
-- Name: idx_sessions_expires_at; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_sessions_expires_at ON dev.sessions USING btree (expires_at);


--
-- Name: idx_sessions_is_active; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_sessions_is_active ON dev.sessions USING btree (is_active);


--
-- Name: idx_sessions_last_activity; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_sessions_last_activity ON dev.sessions USING btree (last_activity);


--
-- Name: idx_sessions_message_count; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_sessions_message_count ON dev.sessions USING btree (message_count);


--
-- Name: idx_sessions_session_id; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_sessions_session_id ON dev.sessions USING btree (session_id);


--
-- Name: idx_sessions_status; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_sessions_status ON dev.sessions USING btree (status);


--
-- Name: idx_sessions_user_id; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_sessions_user_id ON dev.sessions USING btree (user_id);


--
-- Name: idx_span_logs_level; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_span_logs_level ON dev.span_logs USING btree (level);


--
-- Name: idx_span_logs_span_id; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_span_logs_span_id ON dev.span_logs USING btree (span_id);


--
-- Name: idx_span_logs_timestamp; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_span_logs_timestamp ON dev.span_logs USING btree ("timestamp");


--
-- Name: idx_spans_operation_name; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_spans_operation_name ON dev.spans USING btree (operation_name);


--
-- Name: idx_spans_parent_span_id; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_spans_parent_span_id ON dev.spans USING btree (parent_span_id);


--
-- Name: idx_spans_start_time; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_spans_start_time ON dev.spans USING btree (start_time);


--
-- Name: idx_spans_trace_id; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_spans_trace_id ON dev.spans USING btree (trace_id);


--
-- Name: idx_subscriptions_app_id; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_subscriptions_app_id ON dev.subscriptions USING btree (app_id);


--
-- Name: idx_subscriptions_scope; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_subscriptions_scope ON dev.subscriptions USING btree (subscription_scope);


--
-- Name: idx_subscriptions_status; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_subscriptions_status ON dev.subscriptions USING btree (status);


--
-- Name: idx_subscriptions_user_id; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_subscriptions_user_id ON dev.subscriptions USING btree (user_id);


--
-- Name: idx_traces_session_id; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_traces_session_id ON dev.traces USING btree (session_id);


--
-- Name: idx_traces_start_time; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_traces_start_time ON dev.traces USING btree (start_time);


--
-- Name: idx_traces_status; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_traces_status ON dev.traces USING btree (status);


--
-- Name: idx_traces_user_id; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_traces_user_id ON dev.traces USING btree (user_id);


--
-- Name: idx_user_knowledge_created_at; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_user_knowledge_created_at ON dev.user_knowledge USING btree (created_at);


--
-- Name: idx_user_knowledge_metadata; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_user_knowledge_metadata ON dev.user_knowledge USING gin (metadata);


--
-- Name: idx_user_knowledge_user_id; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_user_knowledge_user_id ON dev.user_knowledge USING btree (user_id);


--
-- Name: idx_user_tasks_status; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_user_tasks_status ON dev.user_tasks USING btree (status);


--
-- Name: idx_user_tasks_task_id; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_user_tasks_task_id ON dev.user_tasks USING btree (task_id);


--
-- Name: idx_user_tasks_type; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_user_tasks_type ON dev.user_tasks USING btree (task_type);


--
-- Name: idx_user_tasks_user_id; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_user_tasks_user_id ON dev.user_tasks USING btree (user_id);


--
-- Name: idx_user_usage_records_created_at; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_user_usage_records_created_at ON dev.user_usage_records USING btree (created_at);


--
-- Name: idx_user_usage_records_event_type; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_user_usage_records_event_type ON dev.user_usage_records USING btree (event_type);


--
-- Name: idx_user_usage_records_session_id; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_user_usage_records_session_id ON dev.user_usage_records USING btree (session_id);


--
-- Name: idx_user_usage_records_user_id; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_user_usage_records_user_id ON dev.user_usage_records USING btree (user_id);


--
-- Name: idx_users_auth0_id; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_users_auth0_id ON dev.users USING btree (auth0_id);


--
-- Name: idx_users_email; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_users_email ON dev.users USING btree (email);


--
-- Name: idx_users_user_id; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_users_user_id ON dev.users USING btree (user_id);


--
-- Name: idx_working_active; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_working_active ON dev.working_memories USING btree (user_id, is_active, expires_at) WHERE (is_active = true);


--
-- Name: idx_working_embedding; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_working_embedding ON dev.working_memories USING ivfflat (embedding public.vector_cosine_ops);


--
-- Name: idx_working_priority; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_working_priority ON dev.working_memories USING btree (priority DESC);


--
-- Name: idx_working_user_type; Type: INDEX; Schema: dev; Owner: -
--

CREATE INDEX idx_working_user_type ON dev.working_memories USING btree (user_id, context_type);


--
-- Name: episodic_memories episodic_metadata_trigger; Type: TRIGGER; Schema: dev; Owner: -
--

CREATE TRIGGER episodic_metadata_trigger AFTER INSERT OR UPDATE ON dev.episodic_memories FOR EACH ROW EXECUTE FUNCTION dev.update_memory_metadata();


--
-- Name: factual_memories factual_metadata_trigger; Type: TRIGGER; Schema: dev; Owner: -
--

CREATE TRIGGER factual_metadata_trigger AFTER INSERT OR UPDATE ON dev.factual_memories FOR EACH ROW EXECUTE FUNCTION dev.update_memory_metadata();


--
-- Name: procedural_memories procedural_metadata_trigger; Type: TRIGGER; Schema: dev; Owner: -
--

CREATE TRIGGER procedural_metadata_trigger AFTER INSERT OR UPDATE ON dev.procedural_memories FOR EACH ROW EXECUTE FUNCTION dev.update_memory_metadata();


--
-- Name: semantic_memories semantic_metadata_trigger; Type: TRIGGER; Schema: dev; Owner: -
--

CREATE TRIGGER semantic_metadata_trigger AFTER INSERT OR UPDATE ON dev.semantic_memories FOR EACH ROW EXECUTE FUNCTION dev.update_memory_metadata();


--
-- Name: db_meta_embedding update_db_meta_embedding_updated_at; Type: TRIGGER; Schema: dev; Owner: -
--

CREATE TRIGGER update_db_meta_embedding_updated_at BEFORE UPDATE ON dev.db_meta_embedding FOR EACH ROW EXECUTE FUNCTION dev.update_metadata_embedding_updated_at();


--
-- Name: mcp_unified_search_embeddings update_mcp_unified_search_embeddings_updated_at; Type: TRIGGER; Schema: dev; Owner: -
--

CREATE TRIGGER update_mcp_unified_search_embeddings_updated_at BEFORE UPDATE ON dev.mcp_unified_search_embeddings FOR EACH ROW EXECUTE FUNCTION dev.update_updated_at_column();


--
-- Name: users update_users_updated_at; Type: TRIGGER; Schema: dev; Owner: -
--

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON dev.users FOR EACH ROW EXECUTE FUNCTION dev.update_updated_at_column();


--
-- Name: working_memories working_metadata_trigger; Type: TRIGGER; Schema: dev; Owner: -
--

CREATE TRIGGER working_metadata_trigger AFTER INSERT OR UPDATE ON dev.working_memories FOR EACH ROW EXECUTE FUNCTION dev.update_memory_metadata();


--
-- Name: carts carts_user_id_fkey; Type: FK CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.carts
    ADD CONSTRAINT carts_user_id_fkey FOREIGN KEY (user_id) REFERENCES dev.users(user_id);


--
-- Name: episodic_memories episodic_memories_user_id_fkey; Type: FK CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.episodic_memories
    ADD CONSTRAINT episodic_memories_user_id_fkey FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE;


--
-- Name: events events_task_id_fkey; Type: FK CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.events
    ADD CONSTRAINT events_task_id_fkey FOREIGN KEY (task_id) REFERENCES dev.user_tasks(task_id);


--
-- Name: events events_user_id_fkey; Type: FK CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.events
    ADD CONSTRAINT events_user_id_fkey FOREIGN KEY (user_id) REFERENCES dev.users(user_id);


--
-- Name: factual_memories factual_memories_user_id_fkey; Type: FK CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.factual_memories
    ADD CONSTRAINT factual_memories_user_id_fkey FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE;


--
-- Name: langgraph_executions langgraph_executions_span_id_fkey; Type: FK CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.langgraph_executions
    ADD CONSTRAINT langgraph_executions_span_id_fkey FOREIGN KEY (span_id) REFERENCES dev.spans(span_id);


--
-- Name: langgraph_executions langgraph_executions_trace_id_fkey; Type: FK CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.langgraph_executions
    ADD CONSTRAINT langgraph_executions_trace_id_fkey FOREIGN KEY (trace_id) REFERENCES dev.traces(trace_id);


--
-- Name: langgraph_executions langgraph_executions_user_id_fkey; Type: FK CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.langgraph_executions
    ADD CONSTRAINT langgraph_executions_user_id_fkey FOREIGN KEY (user_id) REFERENCES dev.users(user_id);


--
-- Name: memory_associations memory_associations_user_id_fkey; Type: FK CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.memory_associations
    ADD CONSTRAINT memory_associations_user_id_fkey FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE;


--
-- Name: memory_config memory_config_user_id_fkey; Type: FK CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.memory_config
    ADD CONSTRAINT memory_config_user_id_fkey FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE;


--
-- Name: memory_extraction_logs memory_extraction_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.memory_extraction_logs
    ADD CONSTRAINT memory_extraction_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE;


--
-- Name: memory_metadata memory_metadata_user_id_fkey; Type: FK CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.memory_metadata
    ADD CONSTRAINT memory_metadata_user_id_fkey FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE;


--
-- Name: memory_statistics memory_statistics_user_id_fkey; Type: FK CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.memory_statistics
    ADD CONSTRAINT memory_statistics_user_id_fkey FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE;


--
-- Name: model_capabilities model_capabilities_model_id_fkey; Type: FK CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.model_capabilities
    ADD CONSTRAINT model_capabilities_model_id_fkey FOREIGN KEY (model_id) REFERENCES dev.models(model_id) ON DELETE CASCADE;


--
-- Name: model_embeddings model_embeddings_model_id_fkey; Type: FK CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.model_embeddings
    ADD CONSTRAINT model_embeddings_model_id_fkey FOREIGN KEY (model_id) REFERENCES dev.models(model_id) ON DELETE CASCADE;


--
-- Name: orders orders_user_id_fkey; Type: FK CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.orders
    ADD CONSTRAINT orders_user_id_fkey FOREIGN KEY (user_id) REFERENCES dev.users(user_id);


--
-- Name: procedural_memories procedural_memories_user_id_fkey; Type: FK CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.procedural_memories
    ADD CONSTRAINT procedural_memories_user_id_fkey FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE;


--
-- Name: semantic_memories semantic_memories_parent_concept_id_fkey; Type: FK CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.semantic_memories
    ADD CONSTRAINT semantic_memories_parent_concept_id_fkey FOREIGN KEY (parent_concept_id) REFERENCES dev.semantic_memories(id);


--
-- Name: semantic_memories semantic_memories_user_id_fkey; Type: FK CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.semantic_memories
    ADD CONSTRAINT semantic_memories_user_id_fkey FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE;


--
-- Name: session_memories session_memories_user_id_fkey; Type: FK CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.session_memories
    ADD CONSTRAINT session_memories_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: session_messages session_messages_user_id_fkey; Type: FK CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.session_messages
    ADD CONSTRAINT session_messages_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: sessions sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.sessions
    ADD CONSTRAINT sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES dev.users(user_id);


--
-- Name: span_logs span_logs_span_id_fkey; Type: FK CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.span_logs
    ADD CONSTRAINT span_logs_span_id_fkey FOREIGN KEY (span_id) REFERENCES dev.spans(span_id);


--
-- Name: spans spans_trace_id_fkey; Type: FK CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.spans
    ADD CONSTRAINT spans_trace_id_fkey FOREIGN KEY (trace_id) REFERENCES dev.traces(trace_id);


--
-- Name: subscriptions subscriptions_user_id_fkey; Type: FK CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.subscriptions
    ADD CONSTRAINT subscriptions_user_id_fkey FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE;


--
-- Name: traces traces_session_id_fkey; Type: FK CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.traces
    ADD CONSTRAINT traces_session_id_fkey FOREIGN KEY (session_id) REFERENCES dev.sessions(session_id);


--
-- Name: traces traces_user_id_fkey; Type: FK CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.traces
    ADD CONSTRAINT traces_user_id_fkey FOREIGN KEY (user_id) REFERENCES dev.users(user_id);


--
-- Name: user_credit_transactions user_credit_transactions_usage_record_id_fkey; Type: FK CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.user_credit_transactions
    ADD CONSTRAINT user_credit_transactions_usage_record_id_fkey FOREIGN KEY (usage_record_id) REFERENCES dev.user_usage_records(id) ON DELETE SET NULL;


--
-- Name: user_credit_transactions user_credit_transactions_user_id_fkey; Type: FK CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.user_credit_transactions
    ADD CONSTRAINT user_credit_transactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE;


--
-- Name: user_tasks user_tasks_user_id_fkey; Type: FK CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.user_tasks
    ADD CONSTRAINT user_tasks_user_id_fkey FOREIGN KEY (user_id) REFERENCES dev.users(user_id);


--
-- Name: user_usage_records user_usage_records_user_id_fkey; Type: FK CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.user_usage_records
    ADD CONSTRAINT user_usage_records_user_id_fkey FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE;


--
-- Name: working_memories working_memories_user_id_fkey; Type: FK CONSTRAINT; Schema: dev; Owner: -
--

ALTER TABLE ONLY dev.working_memories
    ADD CONSTRAINT working_memories_user_id_fkey FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

