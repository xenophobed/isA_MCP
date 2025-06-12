from langgraph.graph import StateGraph, START, END 
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.postgres import PostgresStore
from langgraph.store.base import BaseStore
from app.services.ai.models.ai_factory import AIFactory
from typing import Union
from langmem.short_term import SummarizationNode
from langchain_core.messages.utils import count_tokens_approximately
from langchain_core.messages import trim_messages



DB_URL = "postgresql://postgres:postgres@localhost:5432/langgraph"


class MemoryService:
    
    def __init__(self):   
        self.embeddings = AIFactory.get_instance().get_embeddings(model_name="text-embedding-3-small")
        
        self.checkpointer = PostgresSaver.from_conn_string(DB_URL)
        
        self.store = PostgresStore.from_conn_string(DB_URL)
        self.store = self.store(index={
            "embed": self.embeddings,
            "dmis": 1536,
        })
        
        self.summarization_model = AIFactory.get_instance().get_model(model_name="gpt-4o-mini")
        self.summarization_model = self.summarization_model.bind(max_tokens=128)
        
    
    def get_memory(self):
        item = self.store.get(namespace, "a-memory")
        pass
    
    def search_memory(self):
        items = self.store.search()
            namespace,
            filter={"my-key": "my-value"},
            query="language preference"
        )
        
    
    def summarization(self):
        
        summarization_node = SummarizationNode(
            token_counter = count_tokens_approximately, 
            model=self.summarization_model,
            max_tokens=256, 
            max_tokens_before_summary=256,
            max_summary_tokens=128,
        )
        
    def trim_messages(self):
        
        trim_messages(
            messages,
            # Keep the last <= n_count tokens of the messages.
            strategy="last",
            # Remember to adjust based on your model
            # or else pass a custom token_encoder
            token_counter=ChatOpenAI(model="gpt-4"),
            # Remember to adjust based on the desired conversation
            # length
            max_tokens=45,
            # Most chat models expect that chat history starts with either:
            # (1) a HumanMessage or
            # (2) a SystemMessage followed by a HumanMessage
            start_on="human",
            # Most chat models expect that chat history ends with either:
            # (1) a HumanMessage or
            # (2) a ToolMessage
            end_on=("human", "tool"),
            # Usually, we want to keep the SystemMessage
            # if it's present in the original history.
            # The SystemMessage has special instructions for the model.
            include_system=True,
        )
    
    
    def memory_update(self):
        
        """
        Episodic Memory: what is was like receiving your diploma?
        Semantic Memory: The capital of a foreign country?
        Procedural Memory: How to drive a car?
        Working Memory: What happened in the last 5 minutes?
        Sensory Memory: The smell of a restaurant you passed by? 
        Prospective Memory: To pay the rent every month 
        """
        
        pass 
        # update the memory in hot path in real time 
        # update the memory in background for instance 30 min later 
    
    
    def memory_update_profile(self):
        pass
    
    def memory_update_collection(self):
        pass 
    
    def episodic_memory(self):
        
        # few shot example prompting 
        
    def procedural_memory(self):
        
        # Node that *uses* the instructions
        def call_model(state: State, store: BaseStore):
            namespace = ("agent_instructions", )
            instructions = store.get(namespace, key="agent_a")[0]
            # Application logic
            prompt = prompt_template.format(instructions=instructions.value["instructions"])
            ...

        # Node that updates instructions
        def update_instructions(state: State, store: BaseStore):
            namespace = ("instructions",)
            current_instructions = store.search(namespace)[0]
            # Memory logic
            prompt = prompt_template.format(instructions=instructions.value["instructions"], conversation=state["messages"])
            output = llm.invoke(prompt)
            new_instructions = output['new_instructions']
            store.put(("agent_instructions",), "agent_a", {"instructions": new_instructions})
            ...
    
        
    def filter_message(existing: list, updates: Union[list, dict]):
        if isinstance(updates, list):
            return existing + updates 
        elif isinstance(updates, dict) and updates["type"] == "keep":
            # you get to decide what this looks like 
            # for example you could simplify and just accept a string "DELETE" and clear the entire list 
            return existing[updates["from"]:updates["to"]]
        elif isinstance(updates, dict) and updates["type"] == "delete":
            return existing[:updates["from"]] + existing[updates["to"]:]
        else:
            raise ValueError(f"Invalid update type: {updates['type']}")
        
        
    def memory_save(self):
        
        user_id = "my-user"
        application_context = "my-app"
        namespace = (user_id, application_context)
        store.put(
            namespace,
            "a-memory",
            {
                "rules":[
                    "User likes short, direct language",
                    "user only speaks English & python",
                ],
                "my-key": "my-value",
            }
        )
        