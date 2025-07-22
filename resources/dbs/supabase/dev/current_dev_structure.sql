-- Current dev schema structure (READ-ONLY EXPORT)
-- Generated on: Mon Jul 21 15:19:39 PDT 2025
-- This file can be used to create the same structure in other schemas

-- Table: carts
                                           Table "dev.carts"
    Column    |           Type           | Collation | Nullable |                Default                
--------------+--------------------------+-----------+----------+---------------------------------------
 id           | integer                  |           | not null | nextval('dev.carts_id_seq'::regclass)
 cart_id      | character varying(255)   |           | not null | 
 user_id      | character varying(255)   |           |          | 
 cart_data    | jsonb                    |           |          | '{}'::jsonb
 total_amount | numeric(10,2)            |           |          | 0.00
 currency     | character varying(3)     |           |          | 'USD'::character varying
 status       | character varying(50)    |           |          | 'active'::character varying
 created_at   | timestamp with time zone |           |          | now()
 updated_at   | timestamp with time zone |           |          | now()
 expires_at   | timestamp with time zone |           |          | 
Indexes:
    "carts_pkey" PRIMARY KEY, btree (id)
    "carts_cart_id_key" UNIQUE CONSTRAINT, btree (cart_id)
    "idx_carts_expires_at" btree (expires_at)
    "idx_carts_status" btree (status)
    "idx_carts_user_id" btree (user_id)
Foreign-key constraints:
    "carts_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id)


-- Table: checkpoint_blobs
              Table "dev.checkpoint_blobs"
    Column     | Type  | Collation | Nullable | Default  
---------------+-------+-----------+----------+----------
 thread_id     | text  |           | not null | 
 checkpoint_ns | text  |           | not null | ''::text
 channel       | text  |           | not null | 
 version       | text  |           | not null | 
 type          | text  |           | not null | 
 blob          | bytea |           |          | 
Indexes:
    "checkpoint_blobs_pkey" PRIMARY KEY, btree (thread_id, checkpoint_ns, channel, version)
    "checkpoint_blobs_thread_id_idx" btree (thread_id)


-- Table: checkpoint_migrations
         Table "dev.checkpoint_migrations"
 Column |  Type   | Collation | Nullable | Default 
--------+---------+-----------+----------+---------
 v      | integer |           | not null | 
Indexes:
    "checkpoint_migrations_pkey" PRIMARY KEY, btree (v)


-- Table: checkpoint_writes
               Table "dev.checkpoint_writes"
    Column     |  Type   | Collation | Nullable | Default  
---------------+---------+-----------+----------+----------
 thread_id     | text    |           | not null | 
 checkpoint_ns | text    |           | not null | ''::text
 checkpoint_id | text    |           | not null | 
 task_id       | text    |           | not null | 
 idx           | integer |           | not null | 
 channel       | text    |           | not null | 
 type          | text    |           |          | 
 blob          | bytea   |           | not null | 
 task_path     | text    |           | not null | ''::text
Indexes:
    "checkpoint_writes_pkey" PRIMARY KEY, btree (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
    "checkpoint_writes_thread_id_idx" btree (thread_id)


-- Table: checkpoints
                      Table "dev.checkpoints"
        Column        | Type  | Collation | Nullable |   Default   
----------------------+-------+-----------+----------+-------------
 thread_id            | text  |           | not null | 
 checkpoint_ns        | text  |           | not null | ''::text
 checkpoint_id        | text  |           | not null | 
 parent_checkpoint_id | text  |           |          | 
 type                 | text  |           |          | 
 checkpoint           | jsonb |           | not null | 
 metadata             | jsonb |           | not null | '{}'::jsonb
Indexes:
    "checkpoints_pkey" PRIMARY KEY, btree (thread_id, checkpoint_ns, checkpoint_id)
    "checkpoints_thread_id_idx" btree (thread_id)


-- Table: db_meta_embedding
                           Table "dev.db_meta_embedding"
      Column      |           Type           | Collation | Nullable |   Default    
------------------+--------------------------+-----------+----------+--------------
 id               | text                     |           | not null | 
 entity_type      | text                     |           | not null | 
 entity_name      | text                     |           | not null | 
 entity_full_name | text                     |           | not null | 
 content          | text                     |           | not null | 
 embedding        | vector(1536)             |           |          | 
 metadata         | jsonb                    |           |          | '{}'::jsonb
 semantic_tags    | text[]                   |           |          | '{}'::text[]
 confidence_score | double precision         |           |          | 0.0
 source_step      | integer                  |           |          | 2
 database_source  | text                     |           |          | ''::text
 created_at       | timestamp with time zone |           |          | now()
 updated_at       | timestamp with time zone |           |          | now()
Indexes:
    "db_meta_embedding_pkey" PRIMARY KEY, btree (id)
    "db_meta_embedding_confidence_idx" btree (confidence_score)
    "db_meta_embedding_created_at_idx" btree (created_at)
    "db_meta_embedding_entity_name_idx" btree (entity_name)
    "db_meta_embedding_entity_type_idx" btree (entity_type)
    "db_meta_embedding_source_idx" btree (database_source)
    "db_meta_embedding_vector_idx" ivfflat (embedding vector_cosine_ops) WITH (lists='100')
Triggers:
    update_db_meta_embedding_updated_at BEFORE UPDATE ON dev.db_meta_embedding FOR EACH ROW EXECUTE FUNCTION dev.update_metadata_embedding_updated_at()


-- Table: episodic_memories
                               Table "dev.episodic_memories"
       Column        |           Type           | Collation | Nullable |      Default      
---------------------+--------------------------+-----------+----------+-------------------
 id                  | uuid                     |           | not null | gen_random_uuid()
 user_id             | character varying(255)   |           |          | 
 episode_title       | character varying(300)   |           | not null | 
 summary             | text                     |           | not null | 
 participants        | jsonb                    |           |          | '[]'::jsonb
 location            | character varying(200)   |           |          | 
 temporal_context    | character varying(100)   |           |          | 
 key_events          | jsonb                    |           | not null | 
 emotional_context   | character varying(50)    |           |          | 
 outcomes            | jsonb                    |           |          | '[]'::jsonb
 lessons_learned     | text                     |           |          | 
 embedding           | vector(1536)             |           |          | 
 emotional_intensity | double precision         |           |          | 0.5
 recall_frequency    | integer                  |           |          | 0
 last_recalled_at    | timestamp with time zone |           |          | 
 occurred_at         | timestamp with time zone |           | not null | 
 created_at          | timestamp with time zone |           |          | now()
 updated_at          | timestamp with time zone |           |          | now()
Indexes:
    "episodic_memories_pkey" PRIMARY KEY, btree (id)
    "idx_episodic_embedding" ivfflat (embedding vector_cosine_ops)
    "idx_episodic_emotional" btree (emotional_intensity DESC)
    "idx_episodic_location" btree (user_id, location) WHERE location IS NOT NULL
    "idx_episodic_user_time" btree (user_id, occurred_at DESC)
Check constraints:
    "episodic_memories_emotional_intensity_check" CHECK (emotional_intensity >= 0::double precision AND emotional_intensity <= 1::double precision)
Foreign-key constraints:
    "episodic_memories_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE
Triggers:
    episodic_metadata_trigger AFTER INSERT OR UPDATE ON dev.episodic_memories FOR EACH ROW EXECUTE FUNCTION dev.update_memory_metadata()


-- Table: events
                                               Table "dev.events"
     Column     |           Type           | Collation | Nullable |                   Default                   
----------------+--------------------------+-----------+----------+---------------------------------------------
 id             | integer                  |           | not null | nextval('dev.events_id_seq'::regclass)
 event_id       | uuid                     |           |          | uuid_generate_v4()
 task_id        | uuid                     |           |          | 
 user_id        | character varying(255)   |           |          | 
 event_type     | character varying(100)   |           | not null | 
 event_data     | jsonb                    |           |          | 
 source         | character varying(100)   |           |          | 'event_sourcing_service'::character varying
 priority       | integer                  |           |          | 1
 processed      | boolean                  |           |          | false
 processed_at   | timestamp with time zone |           |          | 
 agent_response | jsonb                    |           |          | 
 created_at     | timestamp with time zone |           |          | now()
 updated_at     | timestamp with time zone |           |          | now()
Indexes:
    "events_pkey" PRIMARY KEY, btree (id)
    "idx_events_created_at" btree (created_at)
    "idx_events_event_id" btree (event_id)
    "idx_events_processed" btree (processed)
    "idx_events_task_id" btree (task_id)
    "idx_events_type" btree (event_type)
    "idx_events_user_id" btree (user_id)
Foreign-key constraints:
    "events_task_id_fkey" FOREIGN KEY (task_id) REFERENCES dev.user_tasks(task_id)
    "events_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id)


-- Table: factual_memories
                                Table "dev.factual_memories"
        Column         |           Type           | Collation | Nullable |      Default      
-----------------------+--------------------------+-----------+----------+-------------------
 id                    | uuid                     |           | not null | gen_random_uuid()
 user_id               | character varying(255)   |           |          | 
 fact_type             | character varying(50)    |           | not null | 
 subject               | character varying(200)   |           | not null | 
 predicate             | character varying(200)   |           | not null | 
 object_value          | text                     |           | not null | 
 context               | text                     |           |          | 
 confidence            | double precision         |           |          | 0.8
 source_interaction_id | uuid                     |           |          | 
 embedding             | vector(1536)             |           |          | 
 importance_score      | double precision         |           |          | 0.5
 last_confirmed_at     | timestamp with time zone |           |          | now()
 expires_at            | timestamp with time zone |           |          | 
 is_active             | boolean                  |           |          | true
 created_at            | timestamp with time zone |           |          | now()
 updated_at            | timestamp with time zone |           |          | now()
Indexes:
    "factual_memories_pkey" PRIMARY KEY, btree (id)
    "factual_memories_user_id_fact_type_subject_predicate_key" UNIQUE CONSTRAINT, btree (user_id, fact_type, subject, predicate)
    "idx_factual_embedding" ivfflat (embedding vector_cosine_ops)
    "idx_factual_importance" btree (importance_score DESC)
    "idx_factual_subject" btree (user_id, subject)
    "idx_factual_user_type" btree (user_id, fact_type)
Check constraints:
    "factual_memories_confidence_check" CHECK (confidence >= 0::double precision AND confidence <= 1::double precision)
Foreign-key constraints:
    "factual_memories_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE
Triggers:
    factual_metadata_trigger AFTER INSERT OR UPDATE ON dev.factual_memories FOR EACH ROW EXECUTE FUNCTION dev.update_memory_metadata()


-- Table: langgraph_executions
                                             Table "dev.langgraph_executions"
     Column      |           Type           | Collation | Nullable |                       Default                        
-----------------+--------------------------+-----------+----------+------------------------------------------------------
 id              | integer                  |           | not null | nextval('dev.langgraph_executions_id_seq'::regclass)
 trace_id        | character varying(255)   |           |          | 
 span_id         | character varying(255)   |           |          | 
 user_id         | character varying(255)   |           |          | 
 node_name       | character varying(255)   |           |          | 
 execution_order | integer                  |           |          | 
 input_state     | jsonb                    |           |          | 
 output_state    | jsonb                    |           |          | 
 next_action     | character varying(255)   |           |          | 
 execution_time  | double precision         |           |          | 
 created_at      | timestamp with time zone |           |          | now()
Indexes:
    "langgraph_executions_pkey" PRIMARY KEY, btree (id)
    "idx_langgraph_node_name" btree (node_name)
    "idx_langgraph_span_id" btree (span_id)
    "idx_langgraph_trace_id" btree (trace_id)
    "idx_langgraph_user_id" btree (user_id)
Foreign-key constraints:
    "langgraph_executions_span_id_fkey" FOREIGN KEY (span_id) REFERENCES dev.spans(span_id)
    "langgraph_executions_trace_id_fkey" FOREIGN KEY (trace_id) REFERENCES dev.traces(trace_id)
    "langgraph_executions_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id)


-- Table: mcp_prompts
                                            Table "dev.mcp_prompts"
    Column     |           Type           | Collation | Nullable |                   Default                   
---------------+--------------------------+-----------+----------+---------------------------------------------
 id            | integer                  |           | not null | nextval('dev.mcp_prompts_id_seq'::regclass)
 name          | character varying(255)   |           | not null | 
 description   | text                     |           |          | 
 category      | character varying(100)   |           |          | 
 arguments     | jsonb                    |           |          | '[]'::jsonb
 content       | text                     |           |          | 
 created_at    | timestamp with time zone |           |          | now()
 updated_at    | timestamp with time zone |           |          | now()
 last_modified | timestamp with time zone |           |          | now()
 usage_count   | integer                  |           |          | 0
 is_active     | boolean                  |           |          | true
Indexes:
    "mcp_prompts_pkey" PRIMARY KEY, btree (id)
    "idx_mcp_prompts_active" btree (is_active)
    "idx_mcp_prompts_category" btree (category)
    "mcp_prompts_name_key" UNIQUE CONSTRAINT, btree (name)


-- Table: mcp_resources
                                            Table "dev.mcp_resources"
    Column     |           Type           | Collation | Nullable |                    Default                    
---------------+--------------------------+-----------+----------+-----------------------------------------------
 id            | integer                  |           | not null | nextval('dev.mcp_resources_id_seq'::regclass)
 uri           | character varying(500)   |           | not null | 
 name          | character varying(255)   |           | not null | 
 description   | text                     |           |          | 
 resource_type | character varying(100)   |           |          | 
 mime_type     | character varying(100)   |           |          | 
 size_bytes    | bigint                   |           |          | 0
 created_at    | timestamp with time zone |           |          | now()
 updated_at    | timestamp with time zone |           |          | now()
 last_accessed | timestamp with time zone |           |          | 
 access_count  | integer                  |           |          | 0
 is_active     | boolean                  |           |          | true
Indexes:
    "mcp_resources_pkey" PRIMARY KEY, btree (id)
    "idx_mcp_resources_active" btree (is_active)
    "idx_mcp_resources_type" btree (resource_type)
    "mcp_resources_uri_key" UNIQUE CONSTRAINT, btree (uri)


-- Table: mcp_search_history
                                             Table "dev.mcp_search_history"
      Column      |           Type           | Collation | Nullable |                      Default                       
------------------+--------------------------+-----------+----------+----------------------------------------------------
 id               | integer                  |           | not null | nextval('dev.mcp_search_history_id_seq'::regclass)
 query            | text                     |           | not null | 
 filters          | jsonb                    |           |          | 
 results_count    | integer                  |           |          | 
 top_results      | text[]                   |           |          | 
 result_types     | text[]                   |           |          | 
 user_id          | text                     |           |          | 
 session_id       | text                     |           |          | 
 response_time_ms | integer                  |           |          | 
 created_at       | timestamp with time zone |           |          | now()
Indexes:
    "mcp_search_history_pkey" PRIMARY KEY, btree (id)
    "idx_mcp_search_history_created" btree (created_at)
    "idx_mcp_search_history_query" btree (query)
    "idx_mcp_search_history_user" btree (user_id)


-- Table: mcp_tools
                                              Table "dev.mcp_tools"
      Column       |           Type           | Collation | Nullable |                  Default                  
-------------------+--------------------------+-----------+----------+-------------------------------------------
 id                | integer                  |           | not null | nextval('dev.mcp_tools_id_seq'::regclass)
 name              | character varying(255)   |           | not null | 
 description       | text                     |           |          | 
 category          | character varying(100)   |           |          | 
 input_schema      | jsonb                    |           |          | 
 created_at        | timestamp with time zone |           |          | now()
 updated_at        | timestamp with time zone |           |          | now()
 last_used         | timestamp with time zone |           |          | 
 call_count        | integer                  |           |          | 0
 avg_response_time | integer                  |           |          | 0
 success_rate      | numeric(5,2)             |           |          | 100.0
 is_active         | boolean                  |           |          | true
Indexes:
    "mcp_tools_pkey" PRIMARY KEY, btree (id)
    "idx_mcp_tools_active" btree (is_active)
    "idx_mcp_tools_category" btree (category)
    "mcp_tools_name_key" UNIQUE CONSTRAINT, btree (name)


-- Table: mcp_unified_search_embeddings
                                           Table "dev.mcp_unified_search_embeddings"
   Column    |           Type           | Collation | Nullable |                            Default                            
-------------+--------------------------+-----------+----------+---------------------------------------------------------------
 id          | integer                  |           | not null | nextval('dev.mcp_unified_search_embeddings_id_seq'::regclass)
 item_name   | text                     |           | not null | 
 item_type   | text                     |           | not null | 
 category    | text                     |           | not null | 
 description | text                     |           |          | 
 embedding   | vector(1536)             |           |          | 
 keywords    | text[]                   |           |          | 
 metadata    | jsonb                    |           |          | 
 created_at  | timestamp with time zone |           |          | now()
 updated_at  | timestamp with time zone |           |          | now()
Indexes:
    "mcp_unified_search_embeddings_pkey" PRIMARY KEY, btree (id)
    "idx_mcp_unified_search_embeddings_category" btree (category)
    "idx_mcp_unified_search_embeddings_name" btree (item_name)
    "idx_mcp_unified_search_embeddings_type" btree (item_type)
    "idx_mcp_unified_search_embeddings_updated" btree (updated_at)
    "idx_mcp_unified_search_embeddings_vector" ivfflat (embedding vector_cosine_ops) WITH (lists='100')
    "mcp_unified_search_embeddings_item_name_key" UNIQUE CONSTRAINT, btree (item_name)
Check constraints:
    "mcp_unified_search_embeddings_item_type_check" CHECK (item_type = ANY (ARRAY['tool'::text, 'prompt'::text, 'resource'::text]))
Triggers:
    update_mcp_unified_search_embeddings_updated_at BEFORE UPDATE ON dev.mcp_unified_search_embeddings FOR EACH ROW EXECUTE FUNCTION dev.update_updated_at_column()


-- Table: memory_associations
                             Table "dev.memory_associations"
       Column       |           Type           | Collation | Nullable |      Default      
--------------------+--------------------------+-----------+----------+-------------------
 id                 | uuid                     |           | not null | gen_random_uuid()
 user_id            | character varying(255)   |           |          | 
 source_memory_type | character varying(20)    |           | not null | 
 source_memory_id   | uuid                     |           | not null | 
 target_memory_type | character varying(20)    |           | not null | 
 target_memory_id   | uuid                     |           | not null | 
 association_type   | character varying(50)    |           | not null | 
 strength           | double precision         |           |          | 0.5
 context            | text                     |           |          | 
 auto_discovered    | boolean                  |           |          | false
 confirmation_count | integer                  |           |          | 0
 created_at         | timestamp with time zone |           |          | now()
Indexes:
    "memory_associations_pkey" PRIMARY KEY, btree (id)
    "idx_associations_source" btree (source_memory_type, source_memory_id)
    "idx_associations_strength" btree (strength DESC)
    "idx_associations_target" btree (target_memory_type, target_memory_id)
    "idx_associations_user" btree (user_id)
    "memory_associations_user_id_source_memory_type_source_memor_key" UNIQUE CONSTRAINT, btree (user_id, source_memory_type, source_memory_id, target_memory_type, target_memory_id, association_type)
Check constraints:
    "memory_associations_source_memory_type_check" CHECK (source_memory_type::text = ANY (ARRAY['factual'::character varying, 'procedural'::character varying, 'episodic'::character varying, 'semantic'::character varying, 'working'::character varying]::text[]))
    "memory_associations_strength_check" CHECK (strength >= 0::double precision AND strength <= 1::double precision)
    "memory_associations_target_memory_type_check" CHECK (target_memory_type::text = ANY (ARRAY['factual'::character varying, 'procedural'::character varying, 'episodic'::character varying, 'semantic'::character varying, 'working'::character varying]::text[]))
Foreign-key constraints:
    "memory_associations_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE


-- Table: memory_config
                                     Table "dev.memory_config"
            Column            |           Type           | Collation | Nullable |      Default      
------------------------------+--------------------------+-----------+----------+-------------------
 id                           | uuid                     |           | not null | gen_random_uuid()
 user_id                      | character varying(255)   |           |          | 
 max_factual_memories         | integer                  |           |          | 10000
 max_procedural_memories      | integer                  |           |          | 1000
 default_similarity_threshold | double precision         |           |          | 0.7
 enable_auto_learning         | boolean                  |           |          | true
 created_at                   | timestamp with time zone |           |          | now()
 updated_at                   | timestamp with time zone |           |          | now()
Indexes:
    "memory_config_pkey" PRIMARY KEY, btree (id)
    "memory_config_user_id_key" UNIQUE CONSTRAINT, btree (user_id)
Foreign-key constraints:
    "memory_config_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE


-- Table: memory_extraction_logs
                             Table "dev.memory_extraction_logs"
        Column         |           Type           | Collation | Nullable |      Default      
-----------------------+--------------------------+-----------+----------+-------------------
 id                    | uuid                     |           | not null | gen_random_uuid()
 user_id               | character varying(255)   |           |          | 
 extraction_session_id | uuid                     |           | not null | 
 source_content_hash   | character varying(64)    |           |          | 
 extracted_memories    | jsonb                    |           | not null | 
 extraction_method     | character varying(50)    |           | not null | 
 confidence_score      | double precision         |           |          | 
 created_at            | timestamp with time zone |           |          | now()
Indexes:
    "memory_extraction_logs_pkey" PRIMARY KEY, btree (id)
Foreign-key constraints:
    "memory_extraction_logs_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE


-- Table: memory_metadata
                                     Table "dev.memory_metadata"
       Column        |           Type           | Collation | Nullable |           Default           
---------------------+--------------------------+-----------+----------+-----------------------------
 id                  | uuid                     |           | not null | gen_random_uuid()
 user_id             | character varying(255)   |           |          | 
 memory_type         | character varying(20)    |           | not null | 
 memory_id           | uuid                     |           | not null | 
 access_count        | integer                  |           |          | 0
 last_accessed_at    | timestamp with time zone |           |          | 
 first_accessed_at   | timestamp with time zone |           |          | now()
 modification_count  | integer                  |           |          | 0
 last_modified_at    | timestamp with time zone |           |          | 
 version             | integer                  |           |          | 1
 accuracy_score      | double precision         |           |          | 
 relevance_score     | double precision         |           |          | 
 completeness_score  | double precision         |           |          | 
 user_rating         | integer                  |           |          | 
 user_feedback       | text                     |           |          | 
 feedback_timestamp  | timestamp with time zone |           |          | 
 system_flags        | jsonb                    |           |          | '{}'::jsonb
 priority_level      | integer                  |           |          | 3
 dependency_count    | integer                  |           |          | 0
 reference_count     | integer                  |           |          | 0
 lifecycle_stage     | character varying(20)    |           |          | 'active'::character varying
 auto_expire         | boolean                  |           |          | false
 expire_after_days   | integer                  |           |          | 
 reinforcement_score | double precision         |           |          | 0.0
 learning_curve      | jsonb                    |           |          | '[]'::jsonb
 created_at          | timestamp with time zone |           |          | now()
 updated_at          | timestamp with time zone |           |          | now()
Indexes:
    "memory_metadata_pkey" PRIMARY KEY, btree (id)
    "idx_metadata_access" btree (access_count DESC)
    "idx_metadata_flags" gin (system_flags)
    "idx_metadata_lifecycle" btree (lifecycle_stage)
    "idx_metadata_memory" btree (memory_type, memory_id)
    "idx_metadata_priority" btree (priority_level DESC)
    "idx_metadata_quality" btree (accuracy_score DESC, relevance_score DESC)
    "idx_metadata_user_type" btree (user_id, memory_type)
    "memory_metadata_user_id_memory_type_memory_id_key" UNIQUE CONSTRAINT, btree (user_id, memory_type, memory_id)
Check constraints:
    "memory_metadata_accuracy_score_check" CHECK (accuracy_score >= 0::double precision AND accuracy_score <= 1::double precision)
    "memory_metadata_completeness_score_check" CHECK (completeness_score >= 0::double precision AND completeness_score <= 1::double precision)
    "memory_metadata_lifecycle_stage_check" CHECK (lifecycle_stage::text = ANY (ARRAY['active'::character varying, 'stale'::character varying, 'deprecated'::character varying, 'archived'::character varying]::text[]))
    "memory_metadata_memory_type_check" CHECK (memory_type::text = ANY (ARRAY['factual'::character varying, 'procedural'::character varying, 'episodic'::character varying, 'semantic'::character varying, 'working'::character varying]::text[]))
    "memory_metadata_priority_level_check" CHECK (priority_level >= 1 AND priority_level <= 5)
    "memory_metadata_relevance_score_check" CHECK (relevance_score >= 0::double precision AND relevance_score <= 1::double precision)
    "memory_metadata_user_rating_check" CHECK (user_rating >= 1 AND user_rating <= 5)
Foreign-key constraints:
    "memory_metadata_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE


-- Table: memory_statistics
                             Table "dev.memory_statistics"
      Column      |           Type           | Collation | Nullable |      Default      
------------------+--------------------------+-----------+----------+-------------------
 id               | uuid                     |           | not null | gen_random_uuid()
 user_id          | character varying(255)   |           |          | 
 period_type      | character varying(20)    |           | not null | 
 period_start     | timestamp with time zone |           | not null | 
 period_end       | timestamp with time zone |           | not null | 
 factual_count    | integer                  |           |          | 0
 procedural_count | integer                  |           |          | 0
 episodic_count   | integer                  |           |          | 0
 semantic_count   | integer                  |           |          | 0
 working_count    | integer                  |           |          | 0
 total_accesses   | integer                  |           |          | 0
 created_at       | timestamp with time zone |           |          | now()
Indexes:
    "memory_statistics_pkey" PRIMARY KEY, btree (id)
    "memory_statistics_user_id_period_type_period_start_key" UNIQUE CONSTRAINT, btree (user_id, period_type, period_start)
Check constraints:
    "memory_statistics_period_type_check" CHECK (period_type::text = ANY (ARRAY['daily'::character varying, 'weekly'::character varying, 'monthly'::character varying, 'yearly'::character varying]::text[]))
Foreign-key constraints:
    "memory_statistics_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE


-- Table: model_capabilities
                     Table "dev.model_capabilities"
   Column   |           Type           | Collation | Nullable | Default 
------------+--------------------------+-----------+----------+---------
 model_id   | text                     |           | not null | 
 capability | text                     |           | not null | 
 created_at | timestamp with time zone |           |          | now()
Indexes:
    "model_capabilities_pkey" PRIMARY KEY, btree (model_id, capability)
    "idx_dev_capabilities_capability" btree (capability)
Foreign-key constraints:
    "model_capabilities_model_id_fkey" FOREIGN KEY (model_id) REFERENCES dev.models(model_id) ON DELETE CASCADE


-- Table: model_embeddings
                                           Table "dev.model_embeddings"
   Column    |           Type           | Collation | Nullable |                     Default                      
-------------+--------------------------+-----------+----------+--------------------------------------------------
 id          | bigint                   |           | not null | nextval('dev.model_embeddings_id_seq'::regclass)
 model_id    | text                     |           |          | 
 provider    | text                     |           | not null | 
 description | text                     |           | not null | 
 embedding   | jsonb                    |           |          | 
 created_at  | timestamp with time zone |           |          | now()
 updated_at  | timestamp with time zone |           |          | now()
Indexes:
    "model_embeddings_pkey" PRIMARY KEY, btree (id)
    "idx_dev_embeddings_model_id" btree (model_id)
Foreign-key constraints:
    "model_embeddings_model_id_fkey" FOREIGN KEY (model_id) REFERENCES dev.models(model_id) ON DELETE CASCADE


-- Table: model_statistics
                                               Table "dev.model_statistics"
       Column        |           Type           | Collation | Nullable |                     Default                      
---------------------+--------------------------+-----------+----------+--------------------------------------------------
 id                  | bigint                   |           | not null | nextval('dev.model_statistics_id_seq'::regclass)
 model_id            | text                     |           | not null | 
 provider            | text                     |           | not null | 
 service_type        | text                     |           | not null | 
 operation_type      | text                     |           | not null | 
 date                | date                     |           | not null | CURRENT_DATE
 total_requests      | integer                  |           |          | 0
 total_input_tokens  | bigint                   |           |          | 0
 total_output_tokens | bigint                   |           |          | 0
 total_tokens        | bigint                   |           |          | 0
 total_input_units   | numeric                  |           |          | 0
 total_output_units  | numeric                  |           |          | 0
 total_cost_usd      | numeric(12,8)            |           |          | 0
 last_updated        | timestamp with time zone |           |          | now()
 created_at          | timestamp with time zone |           |          | now()
Indexes:
    "model_statistics_pkey" PRIMARY KEY, btree (id)
    "idx_dev_model_stats_date" btree (date)
    "idx_dev_model_stats_model_id" btree (model_id)
    "idx_dev_model_stats_operation_type" btree (operation_type)
    "idx_dev_model_stats_provider" btree (provider)
    "idx_dev_model_stats_service_type" btree (service_type)
    "unique_model_daily_stats" UNIQUE CONSTRAINT, btree (model_id, provider, service_type, operation_type, date)


-- Table: models
                             Table "dev.models"
   Column   |           Type           | Collation | Nullable |   Default   
------------+--------------------------+-----------+----------+-------------
 model_id   | text                     |           | not null | 
 model_type | text                     |           | not null | 
 provider   | text                     |           | not null | 
 metadata   | jsonb                    |           |          | '{}'::jsonb
 created_at | timestamp with time zone |           |          | now()
 updated_at | timestamp with time zone |           |          | now()
Indexes:
    "models_pkey" PRIMARY KEY, btree (model_id)
    "idx_dev_models_provider" btree (provider)
    "idx_dev_models_type" btree (model_type)
Referenced by:
    TABLE "dev.model_capabilities" CONSTRAINT "model_capabilities_model_id_fkey" FOREIGN KEY (model_id) REFERENCES dev.models(model_id) ON DELETE CASCADE
    TABLE "dev.model_embeddings" CONSTRAINT "model_embeddings_model_id_fkey" FOREIGN KEY (model_id) REFERENCES dev.models(model_id) ON DELETE CASCADE


-- Table: orders
                                              Table "dev.orders"
       Column       |           Type           | Collation | Nullable |                Default                 
--------------------+--------------------------+-----------+----------+----------------------------------------
 id                 | integer                  |           | not null | nextval('dev.orders_id_seq'::regclass)
 order_id           | character varying(255)   |           | not null | 
 user_id            | character varying(255)   |           |          | 
 shopify_order_id   | character varying(255)   |           |          | 
 order_data         | jsonb                    |           |          | '{}'::jsonb
 total_amount       | numeric(10,2)            |           | not null | 
 currency           | character varying(3)     |           |          | 'USD'::character varying
 status             | character varying(50)    |           |          | 'pending'::character varying
 payment_status     | character varying(50)    |           |          | 'unpaid'::character varying
 fulfillment_status | character varying(50)    |           |          | 'unfulfilled'::character varying
 created_at         | timestamp with time zone |           |          | now()
 updated_at         | timestamp with time zone |           |          | now()
Indexes:
    "orders_pkey" PRIMARY KEY, btree (id)
    "idx_orders_created_at" btree (created_at)
    "idx_orders_payment_status" btree (payment_status)
    "idx_orders_shopify_order_id" btree (shopify_order_id)
    "idx_orders_status" btree (status)
    "idx_orders_user_id" btree (user_id)
    "orders_order_id_key" UNIQUE CONSTRAINT, btree (order_id)
Foreign-key constraints:
    "orders_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id)


-- Table: procedural_memories
                               Table "dev.procedural_memories"
         Column         |           Type           | Collation | Nullable |      Default      
------------------------+--------------------------+-----------+----------+-------------------
 id                     | uuid                     |           | not null | gen_random_uuid()
 user_id                | character varying(255)   |           |          | 
 procedure_name         | character varying(200)   |           | not null | 
 domain                 | character varying(100)   |           | not null | 
 trigger_conditions     | jsonb                    |           | not null | 
 steps                  | jsonb                    |           | not null | 
 expected_outcome       | text                     |           |          | 
 success_rate           | double precision         |           |          | 0.0
 usage_count            | integer                  |           |          | 0
 last_used_at           | timestamp with time zone |           |          | 
 embedding              | vector(1536)             |           |          | 
 difficulty_level       | integer                  |           |          | 
 estimated_time_minutes | integer                  |           |          | 
 required_tools         | jsonb                    |           |          | '[]'::jsonb
 created_at             | timestamp with time zone |           |          | now()
 updated_at             | timestamp with time zone |           |          | now()
Indexes:
    "procedural_memories_pkey" PRIMARY KEY, btree (id)
    "idx_procedural_embedding" ivfflat (embedding vector_cosine_ops)
    "idx_procedural_usage" btree (usage_count DESC)
    "idx_procedural_user_domain" btree (user_id, domain)
    "procedural_memories_user_id_procedure_name_domain_key" UNIQUE CONSTRAINT, btree (user_id, procedure_name, domain)
Check constraints:
    "procedural_memories_difficulty_level_check" CHECK (difficulty_level >= 1 AND difficulty_level <= 5)
Foreign-key constraints:
    "procedural_memories_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE
Triggers:
    procedural_metadata_trigger AFTER INSERT OR UPDATE ON dev.procedural_memories FOR EACH ROW EXECUTE FUNCTION dev.update_memory_metadata()


-- Table: prompt_embeddings
                                           Table "dev.prompt_embeddings"
   Column    |           Type           | Collation | Nullable |                      Default                      
-------------+--------------------------+-----------+----------+---------------------------------------------------
 id          | bigint                   |           | not null | nextval('dev.prompt_embeddings_id_seq'::regclass)
 prompt_name | text                     |           | not null | 
 description | text                     |           |          | 
 embedding   | jsonb                    |           |          | 
 created_at  | timestamp with time zone |           |          | now()
 updated_at  | timestamp with time zone |           |          | now()
Indexes:
    "prompt_embeddings_pkey" PRIMARY KEY, btree (id)
    "idx_dev_prompt_embeddings_name" btree (prompt_name)
    "prompt_embeddings_prompt_name_key" UNIQUE CONSTRAINT, btree (prompt_name)


-- Table: resource_embeddings
                                           Table "dev.resource_embeddings"
    Column    |           Type           | Collation | Nullable |                       Default                       
--------------+--------------------------+-----------+----------+-----------------------------------------------------
 id           | bigint                   |           | not null | nextval('dev.resource_embeddings_id_seq'::regclass)
 resource_uri | text                     |           | not null | 
 category     | text                     |           |          | 
 name         | text                     |           |          | 
 description  | text                     |           |          | 
 embedding    | jsonb                    |           |          | 
 created_at   | timestamp with time zone |           |          | now()
 updated_at   | timestamp with time zone |           |          | now()
Indexes:
    "resource_embeddings_pkey" PRIMARY KEY, btree (id)
    "idx_dev_resource_embeddings_category" btree (category)
    "idx_dev_resource_embeddings_uri" btree (resource_uri)
    "resource_embeddings_resource_uri_key" UNIQUE CONSTRAINT, btree (resource_uri)


-- Table: semantic_memories
                              Table "dev.semantic_memories"
       Column       |           Type           | Collation | Nullable |      Default      
--------------------+--------------------------+-----------+----------+-------------------
 id                 | uuid                     |           | not null | gen_random_uuid()
 user_id            | character varying(255)   |           |          | 
 concept_name       | character varying(200)   |           | not null | 
 concept_category   | character varying(100)   |           | not null | 
 definition         | text                     |           | not null | 
 properties         | jsonb                    |           |          | '{}'::jsonb
 related_concepts   | jsonb                    |           |          | '[]'::jsonb
 hierarchical_level | integer                  |           |          | 0
 parent_concept_id  | uuid                     |           |          | 
 use_cases          | jsonb                    |           |          | '[]'::jsonb
 examples           | jsonb                    |           |          | '[]'::jsonb
 embedding          | vector(1536)             |           |          | 
 mastery_level      | double precision         |           |          | 0.5
 learning_source    | character varying(100)   |           |          | 
 created_at         | timestamp with time zone |           |          | now()
 updated_at         | timestamp with time zone |           |          | now()
Indexes:
    "semantic_memories_pkey" PRIMARY KEY, btree (id)
    "idx_semantic_embedding" ivfflat (embedding vector_cosine_ops)
    "idx_semantic_hierarchy" btree (parent_concept_id) WHERE parent_concept_id IS NOT NULL
    "idx_semantic_mastery" btree (mastery_level DESC)
    "idx_semantic_user_category" btree (user_id, concept_category)
    "semantic_memories_user_id_concept_name_concept_category_key" UNIQUE CONSTRAINT, btree (user_id, concept_name, concept_category)
Check constraints:
    "semantic_memories_mastery_level_check" CHECK (mastery_level >= 0::double precision AND mastery_level <= 1::double precision)
Foreign-key constraints:
    "semantic_memories_parent_concept_id_fkey" FOREIGN KEY (parent_concept_id) REFERENCES dev.semantic_memories(id)
    "semantic_memories_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE
Referenced by:
    TABLE "dev.semantic_memories" CONSTRAINT "semantic_memories_parent_concept_id_fkey" FOREIGN KEY (parent_concept_id) REFERENCES dev.semantic_memories(id)
Triggers:
    semantic_metadata_trigger AFTER INSERT OR UPDATE ON dev.semantic_memories FOR EACH ROW EXECUTE FUNCTION dev.update_memory_metadata()


-- Table: session_memories
                                   Table "dev.session_memories"
           Column            |           Type           | Collation | Nullable |      Default      
-----------------------------+--------------------------+-----------+----------+-------------------
 id                          | uuid                     |           | not null | gen_random_uuid()
 session_id                  | character varying(64)    |           | not null | 
 user_id                     | uuid                     |           |          | 
 conversation_summary        | text                     |           |          | 
 user_context                | jsonb                    |           |          | '{}'::jsonb
 key_decisions               | jsonb                    |           |          | '[]'::jsonb
 ongoing_tasks               | jsonb                    |           |          | '[]'::jsonb
 user_preferences            | jsonb                    |           |          | '{}'::jsonb
 important_facts             | jsonb                    |           |          | '[]'::jsonb
 total_messages              | integer                  |           |          | 0
 messages_since_last_summary | integer                  |           |          | 0
 last_summary_at             | timestamp with time zone |           |          | 
 is_active                   | boolean                  |           |          | true
 session_metadata            | jsonb                    |           |          | '{}'::jsonb
 created_at                  | timestamp with time zone |           |          | now()
 updated_at                  | timestamp with time zone |           |          | now()
Indexes:
    "session_memories_pkey" PRIMARY KEY, btree (id)
    "idx_session_memories_active" btree (is_active, updated_at) WHERE is_active = true
    "idx_session_memories_user" btree (user_id)
    "session_memories_session_id_key" UNIQUE CONSTRAINT, btree (session_id)
Foreign-key constraints:
    "session_memories_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE


-- Table: session_messages
                                Table "dev.session_messages"
        Column        |           Type           | Collation | Nullable |      Default      
----------------------+--------------------------+-----------+----------+-------------------
 id                   | uuid                     |           | not null | gen_random_uuid()
 session_id           | character varying(64)    |           | not null | 
 user_id              | uuid                     |           |          | 
 message_type         | character varying(20)    |           | not null | 
 role                 | character varying(20)    |           | not null | 
 content              | text                     |           | not null | 
 tool_calls           | jsonb                    |           |          | 
 tool_call_id         | character varying(100)   |           |          | 
 message_metadata     | jsonb                    |           |          | '{}'::jsonb
 tokens_used          | integer                  |           |          | 0
 cost_usd             | numeric(10,8)            |           |          | 0
 is_summary_candidate | boolean                  |           |          | true
 importance_score     | double precision         |           |          | 0.5
 created_at           | timestamp with time zone |           |          | now()
Indexes:
    "session_messages_pkey" PRIMARY KEY, btree (id)
    "idx_session_messages_session" btree (session_id)
    "idx_session_messages_time" btree (created_at DESC)
    "idx_session_messages_type" btree (message_type)
Foreign-key constraints:
    "session_messages_user_id_fkey" FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE


-- Table: sessions
                                              Table "dev.sessions"
      Column       |           Type           | Collation | Nullable |                 Default                  
-------------------+--------------------------+-----------+----------+------------------------------------------
 id                | integer                  |           | not null | nextval('dev.sessions_id_seq'::regclass)
 session_id        | character varying(255)   |           | not null | 
 user_id           | character varying(255)   |           |          | 
 conversation_data | jsonb                    |           |          | '{}'::jsonb
 status            | character varying(50)    |           |          | 'active'::character varying
 created_at        | timestamp with time zone |           |          | now()
 expires_at        | timestamp with time zone |           |          | 
 updated_at        | timestamp with time zone |           |          | now()
 last_activity     | timestamp with time zone |           |          | now()
 is_active         | boolean                  |           |          | true
 message_count     | integer                  |           |          | 0
 total_tokens      | integer                  |           |          | 0
 total_cost        | numeric(10,6)            |           |          | 0.0
 metadata          | jsonb                    |           |          | '{}'::jsonb
 session_summary   | text                     |           |          | ''::text
Indexes:
    "sessions_pkey" PRIMARY KEY, btree (id)
    "idx_sessions_expires_at" btree (expires_at)
    "idx_sessions_is_active" btree (is_active)
    "idx_sessions_last_activity" btree (last_activity)
    "idx_sessions_message_count" btree (message_count)
    "idx_sessions_session_id" btree (session_id)
    "idx_sessions_status" btree (status)
    "idx_sessions_user_id" btree (user_id)
    "sessions_session_id_key" UNIQUE CONSTRAINT, btree (session_id)
Foreign-key constraints:
    "sessions_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id)
Referenced by:
    TABLE "dev.traces" CONSTRAINT "traces_session_id_fkey" FOREIGN KEY (session_id) REFERENCES dev.sessions(session_id)


-- Table: span_logs
                                          Table "dev.span_logs"
  Column   |           Type           | Collation | Nullable |                  Default                  
-----------+--------------------------+-----------+----------+-------------------------------------------
 id        | integer                  |           | not null | nextval('dev.span_logs_id_seq'::regclass)
 span_id   | character varying(255)   |           |          | 
 timestamp | timestamp with time zone |           |          | now()
 level     | character varying(20)    |           |          | 
 message   | text                     |           |          | 
 fields    | jsonb                    |           |          | '{}'::jsonb
Indexes:
    "span_logs_pkey" PRIMARY KEY, btree (id)
    "idx_span_logs_level" btree (level)
    "idx_span_logs_span_id" btree (span_id)
    "idx_span_logs_timestamp" btree ("timestamp")
Foreign-key constraints:
    "span_logs_span_id_fkey" FOREIGN KEY (span_id) REFERENCES dev.spans(span_id)


-- Table: spans
                                 Table "dev.spans"
     Column     |           Type           | Collation | Nullable |     Default     
----------------+--------------------------+-----------+----------+-----------------
 span_id        | character varying(255)   |           | not null | 
 trace_id       | character varying(255)   |           |          | 
 parent_span_id | character varying(255)   |           |          | 
 operation_name | character varying(255)   |           |          | 
 start_time     | timestamp with time zone |           |          | now()
 end_time       | timestamp with time zone |           |          | 
 duration       | double precision         |           |          | 
 tags           | jsonb                    |           |          | '{}'::jsonb
 created_at     | timestamp with time zone |           |          | now()
 status         | text                     |           |          | 'running'::text
 error_message  | text                     |           |          | 
Indexes:
    "spans_pkey" PRIMARY KEY, btree (span_id)
    "idx_spans_operation_name" btree (operation_name)
    "idx_spans_parent_span_id" btree (parent_span_id)
    "idx_spans_start_time" btree (start_time)
    "idx_spans_trace_id" btree (trace_id)
Check constraints:
    "spans_status_check" CHECK (status = ANY (ARRAY['running'::text, 'completed'::text, 'failed'::text]))
Foreign-key constraints:
    "spans_trace_id_fkey" FOREIGN KEY (trace_id) REFERENCES dev.traces(trace_id)
Referenced by:
    TABLE "dev.langgraph_executions" CONSTRAINT "langgraph_executions_span_id_fkey" FOREIGN KEY (span_id) REFERENCES dev.spans(span_id)
    TABLE "dev.span_logs" CONSTRAINT "span_logs_span_id_fkey" FOREIGN KEY (span_id) REFERENCES dev.spans(span_id)


-- Table: subscriptions
                                                 Table "dev.subscriptions"
         Column          |           Type           | Collation | Nullable |                    Default                    
-------------------------+--------------------------+-----------+----------+-----------------------------------------------
 id                      | integer                  |           | not null | nextval('dev.subscriptions_id_seq'::regclass)
 user_id                 | character varying(255)   |           |          | 
 subscription_scope      | character varying(50)    |           | not null | 
 app_id                  | character varying(255)   |           |          | 
 stripe_subscription_id  | character varying(255)   |           |          | 
 stripe_customer_id      | character varying(255)   |           |          | 
 status                  | character varying(50)    |           |          | 'inactive'::character varying
 plan_type               | character varying(50)    |           |          | 'free'::character varying
 credits_included        | integer                  |           |          | 0
 current_period_start    | timestamp with time zone |           |          | 
 current_period_end      | timestamp with time zone |           |          | 
 canceled_at             | timestamp with time zone |           |          | 
 downgrade_at_period_end | boolean                  |           |          | false
 created_at              | timestamp with time zone |           |          | now()
 updated_at              | timestamp with time zone |           |          | now()
Indexes:
    "subscriptions_pkey" PRIMARY KEY, btree (id)
    "idx_subscriptions_app_id" btree (app_id)
    "idx_subscriptions_scope" btree (subscription_scope)
    "idx_subscriptions_status" btree (status)
    "idx_subscriptions_user_id" btree (user_id)
Foreign-key constraints:
    "subscriptions_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE


-- Table: tool_embeddings
                                           Table "dev.tool_embeddings"
   Column    |           Type           | Collation | Nullable |                     Default                     
-------------+--------------------------+-----------+----------+-------------------------------------------------
 id          | bigint                   |           | not null | nextval('dev.tool_embeddings_id_seq'::regclass)
 tool_name   | text                     |           | not null | 
 description | text                     |           |          | 
 embedding   | jsonb                    |           |          | 
 created_at  | timestamp with time zone |           |          | now()
 updated_at  | timestamp with time zone |           |          | now()
Indexes:
    "tool_embeddings_pkey" PRIMARY KEY, btree (id)
    "idx_dev_tool_embeddings_name" btree (tool_name)
    "tool_embeddings_tool_name_key" UNIQUE CONSTRAINT, btree (tool_name)


-- Table: traces
                                    Table "dev.traces"
     Column     |           Type           | Collation | Nullable |        Default        
----------------+--------------------------+-----------+----------+-----------------------
 trace_id       | character varying(255)   |           | not null | 
 user_id        | character varying(255)   |           |          | 
 session_id     | character varying(255)   |           |          | 
 operation_name | character varying(255)   |           |          | 
 start_time     | timestamp with time zone |           |          | now()
 end_time       | timestamp with time zone |           |          | 
 duration       | double precision         |           |          | 
 status         | character varying(50)    |           |          | 
 tags           | jsonb                    |           |          | '{}'::jsonb
 created_at     | timestamp with time zone |           |          | now()
 service_name   | text                     |           | not null | 'agent-service'::text
 total_spans    | integer                  |           |          | 0
 error_message  | text                     |           |          | 
Indexes:
    "traces_pkey" PRIMARY KEY, btree (trace_id)
    "idx_traces_session_id" btree (session_id)
    "idx_traces_start_time" btree (start_time)
    "idx_traces_status" btree (status)
    "idx_traces_user_id" btree (user_id)
Foreign-key constraints:
    "traces_session_id_fkey" FOREIGN KEY (session_id) REFERENCES dev.sessions(session_id)
    "traces_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id)
Referenced by:
    TABLE "dev.langgraph_executions" CONSTRAINT "langgraph_executions_trace_id_fkey" FOREIGN KEY (trace_id) REFERENCES dev.traces(trace_id)
    TABLE "dev.spans" CONSTRAINT "spans_trace_id_fkey" FOREIGN KEY (trace_id) REFERENCES dev.traces(trace_id)


-- Table: user_credit_transactions
                                             Table "dev.user_credit_transactions"
      Column      |           Type           | Collation | Nullable |                         Default                          
------------------+--------------------------+-----------+----------+----------------------------------------------------------
 id               | bigint                   |           | not null | nextval('dev.user_credit_transactions_id_seq'::regclass)
 user_id          | character varying        |           | not null | 
 transaction_type | character varying        |           | not null | 
 credits_amount   | numeric(10,3)            |           | not null | 
 credits_before   | numeric(10,3)            |           | not null | 
 credits_after    | numeric(10,3)            |           | not null | 
 usage_record_id  | bigint                   |           |          | 
 description      | text                     |           |          | 
 metadata         | jsonb                    |           |          | '{}'::jsonb
 created_at       | timestamp with time zone |           |          | now()
Indexes:
    "user_credit_transactions_pkey" PRIMARY KEY, btree (id)
    "idx_credit_transactions_created_at" btree (created_at)
    "idx_credit_transactions_user_id" btree (user_id)
Foreign-key constraints:
    "user_credit_transactions_usage_record_id_fkey" FOREIGN KEY (usage_record_id) REFERENCES dev.user_usage_records(id) ON DELETE SET NULL
    "user_credit_transactions_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE


-- Table: user_knowledge
                               Table "dev.user_knowledge"
      Column      |           Type           | Collation | Nullable |      Default      
------------------+--------------------------+-----------+----------+-------------------
 id               | uuid                     |           | not null | gen_random_uuid()
 user_id          | text                     |           | not null | 
 text             | text                     |           | not null | 
 embedding_vector | vector(1536)             |           |          | 
 metadata         | jsonb                    |           |          | '{}'::jsonb
 chunk_index      | integer                  |           |          | 0
 source_document  | text                     |           |          | 
 created_at       | timestamp with time zone |           |          | now()
 updated_at       | timestamp with time zone |           |          | now()
Indexes:
    "user_knowledge_pkey" PRIMARY KEY, btree (id)
    "idx_user_knowledge_created_at" btree (created_at)
    "idx_user_knowledge_metadata" gin (metadata)
    "idx_user_knowledge_user_id" btree (user_id)


-- Table: user_tasks
                                           Table "dev.user_tasks"
    Column    |           Type           | Collation | Nullable |                  Default                   
--------------+--------------------------+-----------+----------+--------------------------------------------
 id           | integer                  |           | not null | nextval('dev.user_tasks_id_seq'::regclass)
 task_id      | uuid                     |           |          | uuid_generate_v4()
 user_id      | character varying(255)   |           |          | 
 task_type    | character varying(100)   |           | not null | 
 description  | text                     |           |          | 
 config       | jsonb                    |           |          | 
 callback_url | character varying(500)   |           |          | 
 status       | character varying(50)    |           |          | 'active'::character varying
 last_check   | timestamp with time zone |           |          | 
 next_check   | timestamp with time zone |           |          | 
 created_at   | timestamp with time zone |           |          | now()
 updated_at   | timestamp with time zone |           |          | now()
Indexes:
    "user_tasks_pkey" PRIMARY KEY, btree (id)
    "idx_user_tasks_status" btree (status)
    "idx_user_tasks_task_id" btree (task_id)
    "idx_user_tasks_type" btree (task_type)
    "idx_user_tasks_user_id" btree (user_id)
    "user_tasks_task_id_unique" UNIQUE CONSTRAINT, btree (task_id)
Foreign-key constraints:
    "user_tasks_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id)
Referenced by:
    TABLE "dev.events" CONSTRAINT "events_task_id_fkey" FOREIGN KEY (task_id) REFERENCES dev.user_tasks(task_id)


-- Table: user_usage_records
                                              Table "dev.user_usage_records"
       Column       |           Type           | Collation | Nullable |                      Default                       
--------------------+--------------------------+-----------+----------+----------------------------------------------------
 id                 | bigint                   |           | not null | nextval('dev.user_usage_records_id_seq'::regclass)
 user_id            | character varying        |           | not null | 
 session_id         | character varying        |           |          | 
 trace_id           | character varying        |           |          | 
 endpoint           | character varying        |           | not null | 
 event_type         | character varying        |           | not null | 
 credits_charged    | numeric(10,3)            |           | not null | 0
 cost_usd           | numeric(10,6)            |           | not null | 0
 calculation_method | character varying        |           |          | 'unknown'::character varying
 tokens_used        | integer                  |           |          | 0
 prompt_tokens      | integer                  |           |          | 0
 completion_tokens  | integer                  |           |          | 0
 model_name         | character varying        |           |          | 
 provider           | character varying        |           |          | 
 tool_name          | character varying        |           |          | 
 operation_name     | character varying        |           |          | 
 billing_metadata   | jsonb                    |           |          | '{}'::jsonb
 request_data       | jsonb                    |           |          | '{}'::jsonb
 response_data      | jsonb                    |           |          | '{}'::jsonb
 created_at         | timestamp with time zone |           |          | now()
Indexes:
    "user_usage_records_pkey" PRIMARY KEY, btree (id)
    "idx_user_usage_records_created_at" btree (created_at)
    "idx_user_usage_records_event_type" btree (event_type)
    "idx_user_usage_records_session_id" btree (session_id)
    "idx_user_usage_records_user_id" btree (user_id)
Foreign-key constraints:
    "user_usage_records_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE
Referenced by:
    TABLE "dev.user_credit_transactions" CONSTRAINT "user_credit_transactions_usage_record_id_fkey" FOREIGN KEY (usage_record_id) REFERENCES dev.user_usage_records(id) ON DELETE SET NULL


-- Table: users
                                               Table "dev.users"
       Column        |           Type           | Collation | Nullable |                Default                
---------------------+--------------------------+-----------+----------+---------------------------------------
 id                  | integer                  |           | not null | nextval('dev.users_id_seq'::regclass)
 user_id             | character varying(255)   |           | not null | 
 auth0_id            | character varying(255)   |           |          | 
 email               | character varying(255)   |           |          | 
 phone               | character varying(50)    |           |          | 
 name                | character varying(255)   |           |          | 
 credits_remaining   | numeric(10,3)            |           |          | 1000
 credits_total       | numeric(10,3)            |           |          | 1000
 subscription_status | character varying(50)    |           |          | 'free'::character varying
 is_active           | boolean                  |           |          | true
 shipping_addresses  | jsonb                    |           |          | '[]'::jsonb
 payment_methods     | jsonb                    |           |          | '[]'::jsonb
 preferences         | jsonb                    |           |          | '{}'::jsonb
 created_at          | timestamp with time zone |           |          | now()
 updated_at          | timestamp with time zone |           |          | now()
Indexes:
    "users_pkey" PRIMARY KEY, btree (id)
    "idx_users_auth0_id" btree (auth0_id)
    "idx_users_email" btree (email)
    "idx_users_user_id" btree (user_id)
    "users_auth0_id_key" UNIQUE CONSTRAINT, btree (auth0_id)
    "users_email_key" UNIQUE CONSTRAINT, btree (email)
    "users_user_id_key" UNIQUE CONSTRAINT, btree (user_id)
Referenced by:
    TABLE "dev.carts" CONSTRAINT "carts_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id)
    TABLE "dev.episodic_memories" CONSTRAINT "episodic_memories_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE
    TABLE "dev.events" CONSTRAINT "events_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id)
    TABLE "dev.factual_memories" CONSTRAINT "factual_memories_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE
    TABLE "dev.langgraph_executions" CONSTRAINT "langgraph_executions_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id)
    TABLE "dev.memory_associations" CONSTRAINT "memory_associations_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE
    TABLE "dev.memory_config" CONSTRAINT "memory_config_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE
    TABLE "dev.memory_extraction_logs" CONSTRAINT "memory_extraction_logs_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE
    TABLE "dev.memory_metadata" CONSTRAINT "memory_metadata_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE
    TABLE "dev.memory_statistics" CONSTRAINT "memory_statistics_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE
    TABLE "dev.orders" CONSTRAINT "orders_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id)
    TABLE "dev.procedural_memories" CONSTRAINT "procedural_memories_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE
    TABLE "dev.semantic_memories" CONSTRAINT "semantic_memories_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE
    TABLE "dev.sessions" CONSTRAINT "sessions_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id)
    TABLE "dev.subscriptions" CONSTRAINT "subscriptions_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE
    TABLE "dev.traces" CONSTRAINT "traces_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id)
    TABLE "dev.user_credit_transactions" CONSTRAINT "user_credit_transactions_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE
    TABLE "dev.user_tasks" CONSTRAINT "user_tasks_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id)
    TABLE "dev.user_usage_records" CONSTRAINT "user_usage_records_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE
    TABLE "dev.working_memories" CONSTRAINT "working_memories_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE
Triggers:
    update_users_updated_at BEFORE UPDATE ON dev.users FOR EACH ROW EXECUTE FUNCTION dev.update_updated_at_column()


-- Table: working_memories
                                     Table "dev.working_memories"
       Column        |           Type           | Collation | Nullable |           Default            
---------------------+--------------------------+-----------+----------+------------------------------
 id                  | uuid                     |           | not null | gen_random_uuid()
 user_id             | character varying(255)   |           |          | 
 context_type        | character varying(50)    |           | not null | 
 context_id          | character varying(200)   |           | not null | 
 state_data          | jsonb                    |           | not null | 
 current_step        | character varying(200)   |           |          | 
 progress_percentage | double precision         |           |          | 0.0
 next_actions        | jsonb                    |           |          | '[]'::jsonb
 dependencies        | jsonb                    |           |          | '[]'::jsonb
 blocking_issues     | jsonb                    |           |          | '[]'::jsonb
 embedding           | vector(1536)             |           |          | 
 priority            | integer                  |           |          | 3
 expires_at          | timestamp with time zone |           |          | now() + '24:00:00'::interval
 is_active           | boolean                  |           |          | true
 created_at          | timestamp with time zone |           |          | now()
 updated_at          | timestamp with time zone |           |          | now()
Indexes:
    "working_memories_pkey" PRIMARY KEY, btree (id)
    "idx_working_active" btree (user_id, is_active, expires_at) WHERE is_active = true
    "idx_working_embedding" ivfflat (embedding vector_cosine_ops)
    "idx_working_priority" btree (priority DESC)
    "idx_working_user_type" btree (user_id, context_type)
    "working_memories_user_id_context_type_context_id_key" UNIQUE CONSTRAINT, btree (user_id, context_type, context_id)
Check constraints:
    "working_memories_priority_check" CHECK (priority >= 1 AND priority <= 5)
    "working_memories_progress_percentage_check" CHECK (progress_percentage >= 0::double precision AND progress_percentage <= 100::double precision)
Foreign-key constraints:
    "working_memories_user_id_fkey" FOREIGN KEY (user_id) REFERENCES dev.users(user_id) ON DELETE CASCADE
Triggers:
    working_metadata_trigger AFTER INSERT OR UPDATE ON dev.working_memories FOR EACH ROW EXECUTE FUNCTION dev.update_memory_metadata()


-- Sequences in dev schema:
                          List of relations
 Schema |                 Name                 |   Type   |  Owner   
--------+--------------------------------------+----------+----------
 dev    | carts_id_seq                         | sequence | postgres
 dev    | events_id_seq                        | sequence | postgres
 dev    | langgraph_executions_id_seq          | sequence | postgres
 dev    | mcp_prompts_id_seq                   | sequence | postgres
 dev    | mcp_resources_id_seq                 | sequence | postgres
 dev    | mcp_search_history_id_seq            | sequence | postgres
 dev    | mcp_tools_id_seq                     | sequence | postgres
 dev    | mcp_unified_search_embeddings_id_seq | sequence | postgres
 dev    | model_embeddings_id_seq              | sequence | postgres
 dev    | model_statistics_id_seq              | sequence | postgres
 dev    | orders_id_seq                        | sequence | postgres
 dev    | prompt_embeddings_id_seq             | sequence | postgres
 dev    | resource_embeddings_id_seq           | sequence | postgres
 dev    | sessions_id_seq                      | sequence | postgres
 dev    | span_logs_id_seq                     | sequence | postgres
 dev    | subscriptions_id_seq                 | sequence | postgres
 dev    | tool_embeddings_id_seq               | sequence | postgres
 dev    | user_credit_transactions_id_seq      | sequence | postgres
 dev    | user_tasks_id_seq                    | sequence | postgres
 dev    | user_usage_records_id_seq            | sequence | postgres
 dev    | users_id_seq                         | sequence | postgres
(21 rows)

-- Indexes in dev schema:
                                                      List of relations
 Schema |                              Name                               | Type  |  Owner   |             Table             
--------+-----------------------------------------------------------------+-------+----------+-------------------------------
 dev    | carts_cart_id_key                                               | index | postgres | carts
 dev    | carts_pkey                                                      | index | postgres | carts
 dev    | checkpoint_blobs_pkey                                           | index | postgres | checkpoint_blobs
 dev    | checkpoint_blobs_thread_id_idx                                  | index | postgres | checkpoint_blobs
 dev    | checkpoint_migrations_pkey                                      | index | postgres | checkpoint_migrations
 dev    | checkpoint_writes_pkey                                          | index | postgres | checkpoint_writes
 dev    | checkpoint_writes_thread_id_idx                                 | index | postgres | checkpoint_writes
 dev    | checkpoints_pkey                                                | index | postgres | checkpoints
 dev    | checkpoints_thread_id_idx                                       | index | postgres | checkpoints
 dev    | db_meta_embedding_confidence_idx                                | index | postgres | db_meta_embedding
 dev    | db_meta_embedding_created_at_idx                                | index | postgres | db_meta_embedding
 dev    | db_meta_embedding_entity_name_idx                               | index | postgres | db_meta_embedding
 dev    | db_meta_embedding_entity_type_idx                               | index | postgres | db_meta_embedding
 dev    | db_meta_embedding_pkey                                          | index | postgres | db_meta_embedding
 dev    | db_meta_embedding_source_idx                                    | index | postgres | db_meta_embedding
 dev    | db_meta_embedding_vector_idx                                    | index | postgres | db_meta_embedding
 dev    | episodic_memories_pkey                                          | index | postgres | episodic_memories
 dev    | events_pkey                                                     | index | postgres | events
 dev    | factual_memories_pkey                                           | index | postgres | factual_memories
 dev    | factual_memories_user_id_fact_type_subject_predicate_key        | index | postgres | factual_memories
 dev    | idx_associations_source                                         | index | postgres | memory_associations
 dev    | idx_associations_strength                                       | index | postgres | memory_associations
 dev    | idx_associations_target                                         | index | postgres | memory_associations
 dev    | idx_associations_user                                           | index | postgres | memory_associations
 dev    | idx_carts_expires_at                                            | index | postgres | carts
 dev    | idx_carts_status                                                | index | postgres | carts
 dev    | idx_carts_user_id                                               | index | postgres | carts
 dev    | idx_credit_transactions_created_at                              | index | postgres | user_credit_transactions
 dev    | idx_credit_transactions_user_id                                 | index | postgres | user_credit_transactions
 dev    | idx_dev_capabilities_capability                                 | index | postgres | model_capabilities
 dev    | idx_dev_embeddings_model_id                                     | index | postgres | model_embeddings
 dev    | idx_dev_model_stats_date                                        | index | postgres | model_statistics
 dev    | idx_dev_model_stats_model_id                                    | index | postgres | model_statistics
 dev    | idx_dev_model_stats_operation_type                              | index | postgres | model_statistics
 dev    | idx_dev_model_stats_provider                                    | index | postgres | model_statistics
 dev    | idx_dev_model_stats_service_type                                | index | postgres | model_statistics
 dev    | idx_dev_models_provider                                         | index | postgres | models
 dev    | idx_dev_models_type                                             | index | postgres | models
 dev    | idx_dev_prompt_embeddings_name                                  | index | postgres | prompt_embeddings
 dev    | idx_dev_resource_embeddings_category                            | index | postgres | resource_embeddings
 dev    | idx_dev_resource_embeddings_uri                                 | index | postgres | resource_embeddings
 dev    | idx_dev_tool_embeddings_name                                    | index | postgres | tool_embeddings
 dev    | idx_episodic_embedding                                          | index | postgres | episodic_memories
 dev    | idx_episodic_emotional                                          | index | postgres | episodic_memories
 dev    | idx_episodic_location                                           | index | postgres | episodic_memories
 dev    | idx_episodic_user_time                                          | index | postgres | episodic_memories
 dev    | idx_events_created_at                                           | index | postgres | events
 dev    | idx_events_event_id                                             | index | postgres | events
 dev    | idx_events_processed                                            | index | postgres | events
 dev    | idx_events_task_id                                              | index | postgres | events
 dev    | idx_events_type                                                 | index | postgres | events
 dev    | idx_events_user_id                                              | index | postgres | events
 dev    | idx_factual_embedding                                           | index | postgres | factual_memories
 dev    | idx_factual_importance                                          | index | postgres | factual_memories
 dev    | idx_factual_subject                                             | index | postgres | factual_memories
 dev    | idx_factual_user_type                                           | index | postgres | factual_memories
 dev    | idx_langgraph_node_name                                         | index | postgres | langgraph_executions
 dev    | idx_langgraph_span_id                                           | index | postgres | langgraph_executions
 dev    | idx_langgraph_trace_id                                          | index | postgres | langgraph_executions
 dev    | idx_langgraph_user_id                                           | index | postgres | langgraph_executions
 dev    | idx_mcp_prompts_active                                          | index | postgres | mcp_prompts
 dev    | idx_mcp_prompts_category                                        | index | postgres | mcp_prompts
 dev    | idx_mcp_resources_active                                        | index | postgres | mcp_resources
 dev    | idx_mcp_resources_type                                          | index | postgres | mcp_resources
 dev    | idx_mcp_search_history_created                                  | index | postgres | mcp_search_history
 dev    | idx_mcp_search_history_query                                    | index | postgres | mcp_search_history
 dev    | idx_mcp_search_history_user                                     | index | postgres | mcp_search_history
 dev    | idx_mcp_tools_active                                            | index | postgres | mcp_tools
 dev    | idx_mcp_tools_category                                          | index | postgres | mcp_tools
 dev    | idx_mcp_unified_search_embeddings_category                      | index | postgres | mcp_unified_search_embeddings
 dev    | idx_mcp_unified_search_embeddings_name                          | index | postgres | mcp_unified_search_embeddings
 dev    | idx_mcp_unified_search_embeddings_type                          | index | postgres | mcp_unified_search_embeddings
 dev    | idx_mcp_unified_search_embeddings_updated                       | index | postgres | mcp_unified_search_embeddings
 dev    | idx_mcp_unified_search_embeddings_vector                        | index | postgres | mcp_unified_search_embeddings
 dev    | idx_metadata_access                                             | index | postgres | memory_metadata
 dev    | idx_metadata_flags                                              | index | postgres | memory_metadata
 dev    | idx_metadata_lifecycle                                          | index | postgres | memory_metadata
 dev    | idx_metadata_memory                                             | index | postgres | memory_metadata
 dev    | idx_metadata_priority                                           | index | postgres | memory_metadata
 dev    | idx_metadata_quality                                            | index | postgres | memory_metadata
 dev    | idx_metadata_user_type                                          | index | postgres | memory_metadata
 dev    | idx_orders_created_at                                           | index | postgres | orders
 dev    | idx_orders_payment_status                                       | index | postgres | orders
 dev    | idx_orders_shopify_order_id                                     | index | postgres | orders
 dev    | idx_orders_status                                               | index | postgres | orders
 dev    | idx_orders_user_id                                              | index | postgres | orders
 dev    | idx_procedural_embedding                                        | index | postgres | procedural_memories
 dev    | idx_procedural_usage                                            | index | postgres | procedural_memories
 dev    | idx_procedural_user_domain                                      | index | postgres | procedural_memories
 dev    | idx_semantic_embedding                                          | index | postgres | semantic_memories
 dev    | idx_semantic_hierarchy                                          | index | postgres | semantic_memories
 dev    | idx_semantic_mastery                                            | index | postgres | semantic_memories
 dev    | idx_semantic_user_category                                      | index | postgres | semantic_memories
 dev    | idx_session_memories_active                                     | index | postgres | session_memories
 dev    | idx_session_memories_user                                       | index | postgres | session_memories
 dev    | idx_session_messages_session                                    | index | postgres | session_messages
 dev    | idx_session_messages_time                                       | index | postgres | session_messages
 dev    | idx_session_messages_type                                       | index | postgres | session_messages
 dev    | idx_sessions_expires_at                                         | index | postgres | sessions
 dev    | idx_sessions_is_active                                          | index | postgres | sessions
 dev    | idx_sessions_last_activity                                      | index | postgres | sessions
 dev    | idx_sessions_message_count                                      | index | postgres | sessions
 dev    | idx_sessions_session_id                                         | index | postgres | sessions
 dev    | idx_sessions_status                                             | index | postgres | sessions
 dev    | idx_sessions_user_id                                            | index | postgres | sessions
 dev    | idx_span_logs_level                                             | index | postgres | span_logs
 dev    | idx_span_logs_span_id                                           | index | postgres | span_logs
 dev    | idx_span_logs_timestamp                                         | index | postgres | span_logs
 dev    | idx_spans_operation_name                                        | index | postgres | spans
 dev    | idx_spans_parent_span_id                                        | index | postgres | spans
 dev    | idx_spans_start_time                                            | index | postgres | spans
 dev    | idx_spans_trace_id                                              | index | postgres | spans
 dev    | idx_subscriptions_app_id                                        | index | postgres | subscriptions
 dev    | idx_subscriptions_scope                                         | index | postgres | subscriptions
 dev    | idx_subscriptions_status                                        | index | postgres | subscriptions
 dev    | idx_subscriptions_user_id                                       | index | postgres | subscriptions
 dev    | idx_traces_session_id                                           | index | postgres | traces
 dev    | idx_traces_start_time                                           | index | postgres | traces
 dev    | idx_traces_status                                               | index | postgres | traces
 dev    | idx_traces_user_id                                              | index | postgres | traces
 dev    | idx_user_knowledge_created_at                                   | index | postgres | user_knowledge
 dev    | idx_user_knowledge_metadata                                     | index | postgres | user_knowledge
 dev    | idx_user_knowledge_user_id                                      | index | postgres | user_knowledge
 dev    | idx_user_tasks_status                                           | index | postgres | user_tasks
 dev    | idx_user_tasks_task_id                                          | index | postgres | user_tasks
 dev    | idx_user_tasks_type                                             | index | postgres | user_tasks
 dev    | idx_user_tasks_user_id                                          | index | postgres | user_tasks
 dev    | idx_user_usage_records_created_at                               | index | postgres | user_usage_records
 dev    | idx_user_usage_records_event_type                               | index | postgres | user_usage_records
 dev    | idx_user_usage_records_session_id                               | index | postgres | user_usage_records
 dev    | idx_user_usage_records_user_id                                  | index | postgres | user_usage_records
 dev    | idx_users_auth0_id                                              | index | postgres | users
 dev    | idx_users_email                                                 | index | postgres | users
 dev    | idx_users_user_id                                               | index | postgres | users
 dev    | idx_working_active                                              | index | postgres | working_memories
 dev    | idx_working_embedding                                           | index | postgres | working_memories
 dev    | idx_working_priority                                            | index | postgres | working_memories
 dev    | idx_working_user_type                                           | index | postgres | working_memories
 dev    | langgraph_executions_pkey                                       | index | postgres | langgraph_executions
 dev    | mcp_prompts_name_key                                            | index | postgres | mcp_prompts
 dev    | mcp_prompts_pkey                                                | index | postgres | mcp_prompts
 dev    | mcp_resources_pkey                                              | index | postgres | mcp_resources
 dev    | mcp_resources_uri_key                                           | index | postgres | mcp_resources
 dev    | mcp_search_history_pkey                                         | index | postgres | mcp_search_history
 dev    | mcp_tools_name_key                                              | index | postgres | mcp_tools
 dev    | mcp_tools_pkey                                                  | index | postgres | mcp_tools
 dev    | mcp_unified_search_embeddings_item_name_key                     | index | postgres | mcp_unified_search_embeddings
 dev    | mcp_unified_search_embeddings_pkey                              | index | postgres | mcp_unified_search_embeddings
 dev    | memory_associations_pkey                                        | index | postgres | memory_associations
 dev    | memory_associations_user_id_source_memory_type_source_memor_key | index | postgres | memory_associations
 dev    | memory_config_pkey                                              | index | postgres | memory_config
 dev    | memory_config_user_id_key                                       | index | postgres | memory_config
 dev    | memory_extraction_logs_pkey                                     | index | postgres | memory_extraction_logs
 dev    | memory_metadata_pkey                                            | index | postgres | memory_metadata
 dev    | memory_metadata_user_id_memory_type_memory_id_key               | index | postgres | memory_metadata
 dev    | memory_statistics_pkey                                          | index | postgres | memory_statistics
 dev    | memory_statistics_user_id_period_type_period_start_key          | index | postgres | memory_statistics
 dev    | model_capabilities_pkey                                         | index | postgres | model_capabilities
 dev    | model_embeddings_pkey                                           | index | postgres | model_embeddings
 dev    | model_statistics_pkey                                           | index | postgres | model_statistics
 dev    | models_pkey                                                     | index | postgres | models
 dev    | orders_order_id_key                                             | index | postgres | orders
 dev    | orders_pkey                                                     | index | postgres | orders
 dev    | procedural_memories_pkey                                        | index | postgres | procedural_memories
 dev    | procedural_memories_user_id_procedure_name_domain_key           | index | postgres | procedural_memories
 dev    | prompt_embeddings_pkey                                          | index | postgres | prompt_embeddings
 dev    | prompt_embeddings_prompt_name_key                               | index | postgres | prompt_embeddings
 dev    | resource_embeddings_pkey                                        | index | postgres | resource_embeddings
 dev    | resource_embeddings_resource_uri_key                            | index | postgres | resource_embeddings
 dev    | semantic_memories_pkey                                          | index | postgres | semantic_memories
 dev    | semantic_memories_user_id_concept_name_concept_category_key     | index | postgres | semantic_memories
 dev    | session_memories_pkey                                           | index | postgres | session_memories
 dev    | session_memories_session_id_key                                 | index | postgres | session_memories
 dev    | session_messages_pkey                                           | index | postgres | session_messages
 dev    | sessions_pkey                                                   | index | postgres | sessions
 dev    | sessions_session_id_key                                         | index | postgres | sessions
 dev    | span_logs_pkey                                                  | index | postgres | span_logs
 dev    | spans_pkey                                                      | index | postgres | spans
 dev    | subscriptions_pkey                                              | index | postgres | subscriptions
 dev    | tool_embeddings_pkey                                            | index | postgres | tool_embeddings
 dev    | tool_embeddings_tool_name_key                                   | index | postgres | tool_embeddings
 dev    | traces_pkey                                                     | index | postgres | traces
 dev    | unique_model_daily_stats                                        | index | postgres | model_statistics
 dev    | user_credit_transactions_pkey                                   | index | postgres | user_credit_transactions
 dev    | user_knowledge_pkey                                             | index | postgres | user_knowledge
 dev    | user_tasks_pkey                                                 | index | postgres | user_tasks
 dev    | user_tasks_task_id_unique                                       | index | postgres | user_tasks
 dev    | user_usage_records_pkey                                         | index | postgres | user_usage_records
 dev    | users_auth0_id_key                                              | index | postgres | users
 dev    | users_email_key                                                 | index | postgres | users
 dev    | users_pkey                                                      | index | postgres | users
 dev    | users_user_id_key                                               | index | postgres | users
 dev    | working_memories_pkey                                           | index | postgres | working_memories
 dev    | working_memories_user_id_context_type_context_id_key            | index | postgres | working_memories
(194 rows)

