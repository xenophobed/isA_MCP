"""
CHARACTERIZATION TESTS - DO NOT MODIFY

These tests capture the current behavior of config component interactions.
If these tests fail, it means config integration has changed.
"""

import pytest
import os
from unittest.mock import patch, MagicMock


@pytest.mark.golden
@pytest.mark.component
class TestMCPConfigComponentGolden:
    """Golden tests for MCPConfig as a component - DO NOT MODIFY."""

    def test_mcp_config_initializes_all_sub_configs(self):
        """MCPConfig properly initializes all sub-configurations."""
        from core.config.mcp_config import MCPConfig
        from core.config.infra_config import InfraConfig
        from core.config.logging_config import LoggingConfig
        from core.config.consul_config import ConsulConfig

        config = MCPConfig()

        # All sub-configs should be initialized
        assert config.infrastructure is not None
        assert config.logging is not None
        assert config.consul is not None

        # Sub-configs should be correct types
        assert isinstance(config.infrastructure, InfraConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert isinstance(config.consul, ConsulConfig)

    def test_mcp_config_from_env_propagates_to_sub_configs(self):
        """MCPConfig.from_env() propagates environment to sub-configs."""
        from core.config.mcp_config import MCPConfig

        test_env = {
            "HOST": "192.168.1.1",
            "MCP_PORT": "9999",
            "QDRANT_HOST": "qdrant.test.com",
            "QDRANT_PORT": "6334",
            "REDIS_HOST": "redis.test.com",
        }

        with patch.dict(os.environ, test_env, clear=True):
            config = MCPConfig.from_env()

        # Main config should be set
        assert config.host == "192.168.1.1"
        assert config.port == 9999

        # Sub-config should also be loaded from env
        assert config.infrastructure.qdrant_grpc_host == "qdrant.test.com"
        assert config.infrastructure.qdrant_grpc_port == 6334
        assert config.infrastructure.redis_grpc_host == "redis.test.com"

    def test_mcp_config_sub_configs_have_defaults(self):
        """MCPConfig sub-configs have sensible defaults when env not set."""
        from core.config.mcp_config import MCPConfig

        with patch.dict(os.environ, {}, clear=True):
            config = MCPConfig.from_env()

        # Infrastructure defaults
        assert config.infrastructure.minio_grpc_host == "localhost"
        assert config.infrastructure.qdrant_grpc_host == "localhost"
        assert config.infrastructure.redis_grpc_host == "localhost"
        assert config.infrastructure.postgres_grpc_host == "localhost"


@pytest.mark.golden
@pytest.mark.component
class TestInfraConfigComponentGolden:
    """Golden tests for InfraConfig as a component - DO NOT MODIFY."""

    def test_infra_config_provides_all_service_endpoints(self):
        """InfraConfig provides endpoints for all infrastructure services."""
        from core.config.infra_config import InfraConfig

        config = InfraConfig()

        # All network services should have host and port
        services = [
            ("minio", config.minio_host, config.minio_port),
            ("qdrant", config.qdrant_host, config.qdrant_port),
            ("redis", config.redis_host, config.redis_port),
            ("postgres", config.postgres_host, config.postgres_port),
            ("neo4j", config.neo4j_host, config.neo4j_port),
            ("nats", config.nats_host, config.nats_port),
            ("mqtt", config.mqtt_host, config.mqtt_port),
        ]

        for name, host, port in services:
            assert host is not None, f"{name} host should not be None"
            assert isinstance(port, int), f"{name} port should be int"
            assert port > 0, f"{name} port should be positive"

        # DuckDB is embedded (no network endpoint)
        assert config.duckdb_path is not None

    def test_infra_config_minio_credentials(self):
        """InfraConfig provides MinIO credentials."""
        from core.config.infra_config import InfraConfig

        config = InfraConfig()

        assert config.minio_access_key is not None
        assert config.minio_secret_key is not None
        assert isinstance(config.minio_secure, bool)

    def test_infra_config_optional_url_overrides(self):
        """InfraConfig supports optional URL overrides."""
        from core.config.infra_config import InfraConfig

        with patch.dict(
            os.environ,
            {"QDRANT_URL": "http://qdrant.cloud:6334", "NATS_URL": "nats://nats.cloud:4222"},
            clear=True,
        ):
            config = InfraConfig.from_env()

        assert config.qdrant_url == "http://qdrant.cloud:6334"
        assert config.nats_url == "nats://nats.cloud:4222"


@pytest.mark.golden
@pytest.mark.component
class TestConfigModuleExportsGolden:
    """Golden tests for config module exports - DO NOT MODIFY."""

    def test_config_init_exports_mcp_config(self):
        """core.config exports MCPConfig."""
        from core.config import MCPConfig

        assert MCPConfig is not None

    def test_config_init_exports_infra_config(self):
        """core.config exports InfraConfig."""
        from core.config import InfraConfig

        assert InfraConfig is not None

    def test_config_get_config_singleton(self):
        """core.config provides get_config() for singleton access."""
        try:
            from core.config import get_config

            config1 = get_config()
            config2 = get_config()

            # Should return same instance (singleton)
            assert config1 is config2
        except ImportError:
            # get_config may not exist - that's ok
            pytest.skip("get_config not exported")


@pytest.mark.golden
@pytest.mark.component
class TestConfigValidationGolden:
    """Golden tests for config validation behavior - DO NOT MODIFY."""

    def test_invalid_port_uses_default(self):
        """Invalid port value falls back to default."""
        from core.config.mcp_config import MCPConfig

        with patch.dict(os.environ, {"MCP_PORT": "invalid"}, clear=True):
            config = MCPConfig.from_env()

        assert config.port == 8081  # Default value

    def test_empty_string_bool_is_false(self):
        """Empty string for boolean fields is False."""
        from core.config.mcp_config import MCPConfig

        with patch.dict(os.environ, {"DEBUG": ""}, clear=True):
            config = MCPConfig.from_env()

        assert config.debug is False

    def test_optional_fields_can_be_none(self):
        """Optional fields are None when not set."""
        from core.config.mcp_config import MCPConfig

        with patch.dict(os.environ, {}, clear=True):
            config = MCPConfig.from_env()

        assert config.mcp_api_key is None
        assert config.openai_api_key is None
        assert config.auth_service_url is None
