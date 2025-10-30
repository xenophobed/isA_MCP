#!/usr/bin/env python3
"""Infrastructure services configuration (gRPC)"""
import os
from dataclasses import dataclass
from typing import Optional

def _bool(val: str) -> bool:
    return val.lower() == "true"

def _int(val: str, default: int) -> int:
    try:
        return int(val) if val else default
    except ValueError:
        return default

@dataclass
class InfraConfig:
    """All infrastructure service gRPC endpoints"""
    # MinIO Object Storage
    minio_grpc_host: str = "localhost"
    minio_grpc_port: int = 50051
    minio_endpoint: Optional[str] = None
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False

    # Neo4j Graph Database
    neo4j_grpc_host: str = "localhost"
    neo4j_grpc_port: int = 50063

    # Qdrant Vector Database
    qdrant_grpc_host: str = "localhost"
    qdrant_grpc_port: int = 50062
    qdrant_url: Optional[str] = None

    # Redis Cache
    redis_grpc_host: str = "localhost"
    redis_grpc_port: int = 50055
    redis_db: int = 0

    # PostgreSQL
    postgres_grpc_host: str = "localhost"
    postgres_grpc_port: int = 50061

    # DuckDB Analytics
    duckdb_grpc_host: str = "localhost"
    duckdb_grpc_port: int = 50052

    # NATS Messaging
    nats_grpc_host: str = "localhost"
    nats_grpc_port: int = 50056
    nats_url: Optional[str] = None

    # MQTT Messaging
    mqtt_grpc_host: str = "localhost"
    mqtt_grpc_port: int = 50053
    mqtt_broker: str = "localhost"

    @classmethod
    def from_env(cls) -> 'InfraConfig':
        """Load infrastructure config from environment"""
        return cls(
            # MinIO
            minio_grpc_host=os.getenv("MINIO_GRPC_HOST", "localhost"),
            minio_grpc_port=_int(os.getenv("MINIO_GRPC_PORT", "50051"), 50051),
            minio_endpoint=os.getenv("MINIO_ENDPOINT"),
            minio_access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            minio_secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
            minio_secure=_bool(os.getenv("MINIO_SECURE", "false")),
            # Neo4j
            neo4j_grpc_host=os.getenv("NEO4J_GRPC_HOST", "localhost"),
            neo4j_grpc_port=_int(os.getenv("NEO4J_GRPC_PORT", "50063"), 50063),
            # Qdrant
            qdrant_grpc_host=os.getenv("QDRANT_GRPC_HOST", "localhost"),
            qdrant_grpc_port=_int(os.getenv("QDRANT_GRPC_PORT", "50062"), 50062),
            qdrant_url=os.getenv("QDRANT_URL"),
            # Redis
            redis_grpc_host=os.getenv("REDIS_GRPC_HOST", "localhost"),
            redis_grpc_port=_int(os.getenv("REDIS_GRPC_PORT", "50055"), 50055),
            redis_db=_int(os.getenv("REDIS_DB", "0"), 0),
            # PostgreSQL
            postgres_grpc_host=os.getenv("POSTGRES_GRPC_HOST", "localhost"),
            postgres_grpc_port=_int(os.getenv("POSTGRES_GRPC_PORT", "50061"), 50061),
            # DuckDB
            duckdb_grpc_host=os.getenv("DUCKDB_GRPC_HOST", "localhost"),
            duckdb_grpc_port=_int(os.getenv("DUCKDB_GRPC_PORT", "50052"), 50052),
            # NATS
            nats_grpc_host=os.getenv("NATS_GRPC_HOST", "localhost"),
            nats_grpc_port=_int(os.getenv("NATS_GRPC_PORT", "50056"), 50056),
            nats_url=os.getenv("NATS_URL"),
            # MQTT
            mqtt_grpc_host=os.getenv("MQTT_GRPC_HOST", "localhost"),
            mqtt_grpc_port=_int(os.getenv("MQTT_GRPC_PORT", "50053"), 50053),
            mqtt_broker=os.getenv("MQTT_BROKER", "localhost")
        )
