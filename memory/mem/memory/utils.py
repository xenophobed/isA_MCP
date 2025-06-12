import json

from mem0.configs.prompts import FACT_RETRIEVAL_PROMPT
import logging

logger = logging.getLogger(__name__)


def get_fact_retrieval_messages(message):
    return FACT_RETRIEVAL_PROMPT, f"Input: {message}"


def parse_messages(messages):
    response = ""
    for msg in messages:
        if msg["role"] == "system":
            response += f"system: {msg['content']}\n"
        if msg["role"] == "user":
            response += f"user: {msg['content']}\n"
        if msg["role"] == "assistant":
            response += f"assistant: {msg['content']}\n"
    return response

def format_entities(entities):
    """Format entities for graph representation."""
    formatted_entities = []
    for entity in entities:
        try:
            simplified = f"{entity['source']} -- {entity['relation'].upper()} -- {entity['destination']}"
            formatted_entities.append(simplified)
        except KeyError as e:
            logger.error(f"Missing key in entity: {e}")
            continue
    return formatted_entities