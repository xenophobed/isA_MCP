from app.services.ai.mem.configs.prompts import get_update_memory_messages
from app.services.ai.mem.memory.utils import get_fact_retrieval_messages, parse_messages
from app.services.db.vector.vector_factory import VectorFactory
from app.services.ai.models.ai_factory import AIFactory
from app.config.config_manager import config_manager
from pydantic import BaseModel
import json 
import logging

logger = logging.getLogger(__name__)

class MemoryItem(BaseModel):
    id: str
    memory: str
    hash: str
    created_at: str
    updated_at: str

class EmbedManager:
    def __init__(self):
        self.llm = None
        self.embedding_model = None
        self.vector_store = None
        self.custom_prompt = None
        self.collection_name = None    
        
    async def init(self):
        self.llm_config = config_manager.get_config('llm')
        self.vector_config = config_manager.get_config('qdrant')
        self.llm = AIFactory.get_instance().get_llm(
            model_name="llama3.1",
            provider="ollama",
            config=self.llm_config
        )
        self.embedding_model = AIFactory.get_instance().get_embed_service(
            model_name="bge-m3",
            provider="ollama"
        )
        self.vector_store = await VectorFactory.create_vector_service(
            "qdrant",
            self.vector_config
        )
        
    def _add_to_vector_store(self, messages, metadata, filters):
        parsed_messages = parse_messages(messages)

        if self.custom_prompt:
            system_prompt = self.custom_prompt
            user_prompt = f"Input: {parsed_messages}"
        else:
            system_prompt, user_prompt = get_fact_retrieval_messages(parsed_messages)

        response = self.llm.generate_response(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )

        try:
            new_retrieved_facts = json.loads(response)["facts"]
        except Exception as e:
            logging.error(f"Error in new_retrieved_facts: {e}")
            new_retrieved_facts = []

        retrieved_old_memory = []
        new_message_embeddings = {}
        for new_mem in new_retrieved_facts:
            messages_embeddings = self.embedding_model.embed(new_mem)
            new_message_embeddings[new_mem] = messages_embeddings
            existing_memories = self.vector_store.search(
                query=messages_embeddings,
                limit=5,
                filters=filters,
            )
            for mem in existing_memories:
                retrieved_old_memory.append({"id": mem.id, "text": mem.payload["data"]})

        logging.info(f"Total existing memories: {len(retrieved_old_memory)}")

        # mapping UUIDs with integers for handling UUID hallucinations
        temp_uuid_mapping = {}
        for idx, item in enumerate(retrieved_old_memory):
            temp_uuid_mapping[str(idx)] = item["id"]
            retrieved_old_memory[idx]["id"] = str(idx)

        function_calling_prompt = get_update_memory_messages(retrieved_old_memory, new_retrieved_facts)

        new_memories_with_actions = self.llm.generate_response(
            messages=[{"role": "user", "content": function_calling_prompt}],
            response_format={"type": "json_object"},
        )
        new_memories_with_actions = json.loads(new_memories_with_actions)

        returned_memories = []
        try:
            for resp in new_memories_with_actions["memory"]:
                logging.info(resp)
                try:
                    if resp["event"] == "ADD":
                        memory_id = self._create_memory(
                            data=resp["text"], existing_embeddings=new_message_embeddings, metadata=metadata
                        )
                        returned_memories.append(
                            {
                                "id": memory_id,
                                "memory": resp["text"],
                                "event": resp["event"],
                            }
                        )
                    elif resp["event"] == "UPDATE":
                        self._update_memory(
                            memory_id=temp_uuid_mapping[resp["id"]],
                            data=resp["text"],
                            existing_embeddings=new_message_embeddings,
                            metadata=metadata,
                        )
                        returned_memories.append(
                            {
                                "id": temp_uuid_mapping[resp["id"]],
                                "memory": resp["text"],
                                "event": resp["event"],
                                "previous_memory": resp["old_memory"],
                            }
                        )
                    elif resp["event"] == "DELETE":
                        self._delete_memory(memory_id=temp_uuid_mapping[resp["id"]])
                        returned_memories.append(
                            {
                                "id": temp_uuid_mapping[resp["id"]],
                                "memory": resp["text"],
                                "event": resp["event"],
                            }
                        )
                    elif resp["event"] == "NONE":
                        logging.info("NOOP for Memory.")
                except Exception as e:
                    logging.error(f"Error in new_memories_with_actions: {e}")
        except Exception as e:
            logging.error(f"Error in new_memories_with_actions: {e}")

        return returned_memories
    
    def _search_vector_store(self, query, limit, filters):
        embeddings = self.embedding_model.embed(query)
        memories = self.vector_store.search(query=embeddings, limit=limit, filters=filters)

        excluded_keys = {
            "user_id",
            "agent_id",
            "run_id",
            "hash",
            "data",
            "created_at",
            "updated_at",
        }

        original_memories = [
            {
                **MemoryItem(
                    id=mem.id,
                    memory=mem.payload["data"],
                    hash=mem.payload.get("hash"),
                    created_at=mem.payload.get("created_at"),
                    updated_at=mem.payload.get("updated_at"),
                    score=mem.score,
                ).model_dump(),
                **{key: mem.payload[key] for key in ["user_id", "agent_id", "run_id"] if key in mem.payload},
                **(
                    {"metadata": {k: v for k, v in mem.payload.items() if k not in excluded_keys}}
                    if any(k for k in mem.payload if k not in excluded_keys)
                    else {}
                ),
            }
            for mem in memories
        ]

        return original_memories