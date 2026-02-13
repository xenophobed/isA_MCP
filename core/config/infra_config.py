#!/usr/bin/env python3
"""Infrastructure services configuration (Native drivers - isa-common 0.3.0)"""

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
    """All infrastructure service endpoints (native drivers)"""

    # MinIO Object Storage (native S3 - port 9000)
    minio_host: str = "localhost"
    minio_port: int = 9000
    minio_endpoint: Optional[str] = None
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False

    # Neo4j Graph Database (native bolt - port 7687)
    neo4j_host: str = "localhost"
    neo4j_port: int = 7687

    # Qdrant Vector Database (native HTTP - port 6333)
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_url: Optional[str] = None

    # Redis Cache (native - port 6379)
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    # PostgreSQL (native asyncpg - port 5432)
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "postgres"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"

    # DuckDB Analytics (embedded - no network)
    duckdb_path: str = ":memory:"

    # NATS Messaging (native - port 4222)
    nats_host: str = "localhost"
    nats_port: int = 4222
    nats_url: Optional[str] = None

    # MQTT Messaging (native - port 1883)
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883

    # Backward compatibility aliases (deprecated - will be removed in 1.0.0)
    @property
    def postgres_grpc_host(self) -> str:
        return self.postgres_host

    @property
    def postgres_grpc_port(self) -> int:
        return self.postgres_port

    @property
    def qdrant_grpc_host(self) -> str:
        return self.qdrant_host

    @property
    def qdrant_grpc_port(self) -> int:
        return self.qdrant_port

    @property
    def redis_grpc_host(self) -> str:
        return self.redis_host

    @property
    def redis_grpc_port(self) -> int:
        return self.redis_port

    @property
    def minio_grpc_host(self) -> str:
        return self.minio_host

    @property
    def minio_grpc_port(self) -> int:
        return self.minio_port

    @property
    def neo4j_grpc_host(self) -> str:
        return self.neo4j_host

    @property
    def neo4j_grpc_port(self) -> int:
        return self.neo4j_port

    @property
    def nats_grpc_host(self) -> str:
        return self.nats_host

    @property
    def nats_grpc_port(self) -> int:
        return self.nats_port

    @property
    def mqtt_grpc_host(self) -> str:
        return self.mqtt_host

    @property
    def mqtt_grpc_port(self) -> int:
        return self.mqtt_port

    @classmethod
    def from_env(cls) -> "InfraConfig":
        """Load configuration from environment variables"""
        return cls(
            # MinIO (native S3)
            minio_host=os.getenv("MINIO_HOST", "localhost"),
            minio_port=_int(os.getenv("MINIO_PORT", "9000"), 9000),
            minio_endpoint=os.getenv("MINIO_ENDPOINT"),
            minio_access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            minio_secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
            minio_secure=_bool(os.getenv("MINIO_SECURE", "false")),
            # Neo4j (native bolt)
            neo4j_host=os.getenv("NEO4J_HOST", "localhost"),
            neo4j_port=_int(os.getenv("NEO4J_PORT", "7687"), 7687),
            # Qdrant (native HTTP)
            qdrant_host=os.getenv("QDRANT_HOST", "localhost"),
            qdrant_port=_int(os.getenv("QDRANT_PORT", "6333"), 6333),
            qdrant_url=os.getenv("QDRANT_URL"),
            # Redis (native)
            redis_host=os.getenv("REDIS_HOST", "localhost"),
            redis_port=_int(os.getenv("REDIS_PORT", "6379"), 6379),
            redis_db=_int(os.getenv("REDIS_DB", "0"), 0),
            # PostgreSQL (native asyncpg)
            postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
            postgres_port=_int(os.getenv("POSTGRES_PORT", "5432"), 5432),
            postgres_db=os.getenv("POSTGRES_DB", "postgres"),
            postgres_user=os.getenv("POSTGRES_USER", "postgres"),
            postgres_password=os.getenv("POSTGRES_PASSWORD", "postgres"),
            # DuckDB (embedded)
            duckdb_path=os.getenv("DUCKDB_PATH", ":memory:"),
            # NATS (native)
            nats_host=os.getenv("NATS_HOST", "localhost"),
            nats_port=_int(os.getenv("NATS_PORT", "4222"), 4222),
            nats_url=os.getenv("NATS_URL"),
            # MQTT (native)
            mqtt_host=os.getenv("MQTT_HOST", "localhost"),
            mqtt_port=_int(os.getenv("MQTT_PORT", "1883"), 1883),
        )
