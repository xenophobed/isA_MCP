#!/usr/bin/env python3
"""Infrastructure services configuration (gRPC)"""
import os
import logging
from dataclasses import dataclass, field
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

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

    # Internal state (not loaded from env)
    _consul_registry: Optional[any] = field(default=None, init=False, repr=False)

    def _get_consul_registry(self):
        """Get or create Consul registry instance (lazy initialization)"""
        if self._consul_registry is None:
            try:
                # Import here to avoid circular dependency
                from core.config import get_settings
                from isa_common.consul_client import ConsulRegistry

                settings = get_settings()
                if not settings.consul.enabled:
                    logger.debug("Consul service discovery is disabled")
                    return None

                self._consul_registry = ConsulRegistry(
                    service_name="mcp_service",
                    service_port=8081,
                    consul_host=settings.consul.host,
                    consul_port=settings.consul.port
                )
                logger.debug(f"Consul registry initialized: {settings.consul.host}:{settings.consul.port}")
            except Exception as e:
                logger.warning(f"Failed to initialize Consul registry: {e}")
                self._consul_registry = None
        return self._consul_registry

    def discover_service(
        self,
        service_name: str,
        default_host: str = "localhost",
        default_port: Optional[int] = None,
        env_host_key: Optional[str] = None,
        env_port_key: Optional[str] = None
    ) -> Tuple[str, Optional[int]]:
        """
        Discover service host and port using priority:
        1. Environment variables (e.g., POSTGRES_HOST, POSTGRES_PORT)
        2. Consul service discovery
        3. Default fallback (localhost)

        Args:
            service_name: Name of service in Consul (e.g., 'postgres_grpc_service')
            default_host: Default host if not found
            default_port: Default port if not found
            env_host_key: Environment variable key for host (e.g., 'POSTGRES_HOST')
            env_port_key: Environment variable key for port (e.g., 'POSTGRES_PORT')

        Returns:
            Tuple of (host, port)

        Example:
            >>> from core.config import get_settings
            >>> settings = get_settings()
            >>> host, port = settings.infrastructure.discover_service(
            ...     service_name='postgres_grpc_service',
            ...     default_host='isa-postgres-grpc',
            ...     default_port=50061,
            ...     env_host_key='POSTGRES_HOST',
            ...     env_port_key='POSTGRES_PORT'
            ... )
        """
        # Priority 1: Check environment variables
        env_host = os.getenv(env_host_key) if env_host_key else None
        env_port = os.getenv(env_port_key) if env_port_key else None

        if env_host:
            port = int(env_port) if env_port else default_port
            logger.info(f"Service {service_name} from env: {env_host}:{port}")
            return env_host, port

        # Priority 2: Consul service discovery
        consul = self._get_consul_registry()
        if consul:
            try:
                endpoint = consul.get_service_endpoint(service_name)
                if endpoint:
                    # Parse endpoint: http://host:port or host:port
                    endpoint = endpoint.replace("http://", "").replace("https://", "")
                    if ":" in endpoint:
                        host, port_str = endpoint.rsplit(":", 1)
                        port = int(port_str)
                    else:
                        host = endpoint
                        port = default_port

                    logger.info(f"Service {service_name} discovered via Consul: {host}:{port}")
                    return host, port
                else:
                    logger.debug(f"Service {service_name} not found in Consul")
            except Exception as e:
                logger.warning(f"Consul service discovery failed for {service_name}: {e}")

        # Priority 3: Default fallback
        logger.info(f"Service {service_name} using fallback: {default_host}:{default_port}")
        return default_host, default_port

    @classmethod
    def from_env(cls) -> 'InfraConfig':
        """Load infrastructure config from environment with service discovery"""
        # Create temporary instance to use discover_service
        config = cls.__new__(cls)
        config._consul_registry = None

        # Discover PostgreSQL
        postgres_host, postgres_port = config.discover_service(
            service_name='postgres_grpc_service',
            default_host='isa-postgres-grpc',
            default_port=50061,
            env_host_key='POSTGRES_HOST',
            env_port_key='POSTGRES_PORT'
        )

        # Discover Redis
        redis_host, redis_port = config.discover_service(
            service_name='redis_grpc_service',
            default_host='isa-redis-grpc',
            default_port=50055,
            env_host_key='REDIS_HOST',
            env_port_key='REDIS_PORT'
        )

        # Discover Qdrant
        qdrant_host, qdrant_port = config.discover_service(
            service_name='qdrant_grpc_service',
            default_host='isa-qdrant-grpc',
            default_port=50062,
            env_host_key='QDRANT_HOST',
            env_port_key='QDRANT_PORT'
        )

        # Discover DuckDB
        duckdb_host, duckdb_port = config.discover_service(
            service_name='duckdb_grpc_service',
            default_host='isa-duckdb-grpc',
            default_port=50052,
            env_host_key='DUCKDB_HOST',
            env_port_key='DUCKDB_PORT'
        )

        # Discover MinIO
        minio_host, minio_port = config.discover_service(
            service_name='minio_grpc_service',
            default_host='isa-minio-grpc',
            default_port=50051,
            env_host_key='MINIO_HOST',
            env_port_key='MINIO_PORT'
        )

        # Discover Neo4j
        neo4j_host, neo4j_port = config.discover_service(
            service_name='neo4j_grpc_service',
            default_host='isa-neo4j-grpc',
            default_port=50063,
            env_host_key='NEO4J_HOST',
            env_port_key='NEO4J_PORT'
        )

        # Discover NATS
        nats_host, nats_port = config.discover_service(
            service_name='nats_grpc_service',
            default_host='isa-nats-grpc',
            default_port=50056,
            env_host_key='NATS_HOST',
            env_port_key='NATS_PORT'
        )

        # Discover MQTT
        mqtt_host, mqtt_port = config.discover_service(
            service_name='mqtt_grpc_service',
            default_host='isa-mqtt-grpc',
            default_port=50053,
            env_host_key='MQTT_HOST',
            env_port_key='MQTT_PORT'
        )

        return cls(
            # MinIO
            minio_grpc_host=minio_host,
            minio_grpc_port=minio_port,
            minio_endpoint=os.getenv("MINIO_ENDPOINT"),
            minio_access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            minio_secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
            minio_secure=_bool(os.getenv("MINIO_SECURE", "false")),
            # Neo4j
            neo4j_grpc_host=neo4j_host,
            neo4j_grpc_port=neo4j_port,
            # Qdrant
            qdrant_grpc_host=qdrant_host,
            qdrant_grpc_port=qdrant_port,
            qdrant_url=os.getenv("QDRANT_URL"),
            # Redis
            redis_grpc_host=redis_host,
            redis_grpc_port=redis_port,
            redis_db=_int(os.getenv("REDIS_DB", "0"), 0),
            # PostgreSQL
            postgres_grpc_host=postgres_host,
            postgres_grpc_port=postgres_port,
            # DuckDB
            duckdb_grpc_host=duckdb_host,
            duckdb_grpc_port=duckdb_port,
            # NATS
            nats_grpc_host=nats_host,
            nats_grpc_port=nats_port,
            nats_url=os.getenv("NATS_URL"),
            # MQTT
            mqtt_grpc_host=mqtt_host,
            mqtt_grpc_port=mqtt_port,
            mqtt_broker=os.getenv("MQTT_BROKER", "localhost")
        )
