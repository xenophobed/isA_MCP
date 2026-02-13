"""
CHARACTERIZATION TESTS - DO NOT MODIFY

These tests capture the current behavior of MCPConfig and InfraConfig.
If these tests fail, it means the configuration interface has changed.
"""

import pytest
import dataclasses
import os
from unittest.mock import patch


@pytest.mark.golden
class TestMCPConfigDataclassGolden:
    """Golden tests for MCPConfig dataclass structure - DO NOT MODIFY."""

    def test_mcp_config_is_dataclass(self):
        """MCPConfig must be a dataclass."""
        from core.config.mcp_config import MCPConfig

        assert dataclasses.is_dataclass(MCPConfig)

    def test_mcp_config_has_server_fields(self):
        """MCPConfig must have server configuration fields."""
        from core.config.mcp_config import MCPConfig

        fields = {f.name for f in dataclasses.fields(MCPConfig)}

        assert "host" in fields
        assert "port" in fields
        assert "server_name" in fields
        assert "debug" in fields

    def test_mcp_config_has_auth_fields(self):
        """MCPConfig must have authentication fields."""
        from core.config.mcp_config import MCPConfig

        fields = {f.name for f in dataclasses.fields(MCPConfig)}

        assert "require_auth" in fields
        assert "require_mcp_auth" in fields
        assert "mcp_api_key" in fields
        assert "auth_service_url" in fields

    def test_mcp_config_has_external_api_fields(self):
        """MCPConfig must have external API key fields."""
        from core.config.mcp_config import MCPConfig

        fields = {f.name for f in dataclasses.fields(MCPConfig)}

        assert "openai_api_key" in fields
        assert "brave_api_key" in fields
        assert "composio_api_key" in fields

    def test_mcp_config_has_isa_service_fields(self):
        """MCPConfig must have ISA service fields."""
        from core.config.mcp_config import MCPConfig

        fields = {f.name for f in dataclasses.fields(MCPConfig)}

        assert "isa_service_url" in fields
        assert "isa_api_key" in fields
        assert "require_isa_auth" in fields

    def test_mcp_config_has_sub_configs(self):
        """MCPConfig must have sub-configuration objects."""
        from core.config.mcp_config import MCPConfig

        fields = {f.name for f in dataclasses.fields(MCPConfig)}

        assert "logging" in fields
        assert "infrastructure" in fields
        assert "consul" in fields

    def test_mcp_config_default_values(self):
        """MCPConfig default values match expected."""
        from core.config.mcp_config import MCPConfig

        config = MCPConfig()

        assert config.host == "0.0.0.0"
        assert config.port == 8081
        assert config.server_name == "MCP Server"
        assert config.debug is False
        assert config.require_auth is False
        assert config.require_mcp_auth is False

    def test_mcp_config_from_env_classmethod_exists(self):
        """MCPConfig must have from_env classmethod."""
        from core.config.mcp_config import MCPConfig

        assert hasattr(MCPConfig, "from_env")
        assert callable(MCPConfig.from_env)


@pytest.mark.golden
class TestMCPConfigFromEnvGolden:
    """Golden tests for MCPConfig.from_env() - DO NOT MODIFY."""

    def test_from_env_returns_mcp_config(self):
        """from_env() must return MCPConfig instance."""
        from core.config.mcp_config import MCPConfig

        with patch.dict(os.environ, {}, clear=True):
            config = MCPConfig.from_env()

        assert isinstance(config, MCPConfig)

    def test_from_env_reads_host(self):
        """from_env() reads HOST environment variable."""
        from core.config.mcp_config import MCPConfig

        with patch.dict(os.environ, {"HOST": "127.0.0.1"}, clear=True):
            config = MCPConfig.from_env()

        assert config.host == "127.0.0.1"

    def test_from_env_reads_port(self):
        """from_env() reads MCP_PORT environment variable."""
        from core.config.mcp_config import MCPConfig

        with patch.dict(os.environ, {"MCP_PORT": "9000"}, clear=True):
            config = MCPConfig.from_env()

        assert config.port == 9000

    def test_from_env_reads_debug(self):
        """from_env() reads DEBUG environment variable as bool."""
        from core.config.mcp_config import MCPConfig

        with patch.dict(os.environ, {"DEBUG": "true"}, clear=True):
            config = MCPConfig.from_env()

        assert config.debug is True

    def test_from_env_reads_require_auth(self):
        """from_env() reads REQUIRE_AUTH environment variable."""
        from core.config.mcp_config import MCPConfig

        with patch.dict(os.environ, {"REQUIRE_AUTH": "true"}, clear=True):
            config = MCPConfig.from_env()

        assert config.require_auth is True

    def test_from_env_reads_api_keys(self):
        """from_env() reads API key environment variables."""
        from core.config.mcp_config import MCPConfig

        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "sk-test",
                "BRAVE_TOKEN": "brave-test",
                "COMPOSIO_API_KEY": "composio-test",
            },
            clear=True,
        ):
            config = MCPConfig.from_env()

        assert config.openai_api_key == "sk-test"
        assert config.brave_api_key == "brave-test"
        assert config.composio_api_key == "composio-test"

    def test_from_env_loads_sub_configs(self):
        """from_env() loads sub-configuration objects."""
        from core.config.mcp_config import MCPConfig
        from core.config.infra_config import InfraConfig
        from core.config.logging_config import LoggingConfig
        from core.config.consul_config import ConsulConfig

        with patch.dict(os.environ, {}, clear=True):
            config = MCPConfig.from_env()

        assert isinstance(config.infrastructure, InfraConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert isinstance(config.consul, ConsulConfig)


@pytest.mark.golden
class TestInfraConfigDataclassGolden:
    """Golden tests for InfraConfig dataclass structure - DO NOT MODIFY."""

    def test_infra_config_is_dataclass(self):
        """InfraConfig must be a dataclass."""
        from core.config.infra_config import InfraConfig

        assert dataclasses.is_dataclass(InfraConfig)

    def test_infra_config_has_minio_fields(self):
        """InfraConfig must have MinIO configuration fields."""
        from core.config.infra_config import InfraConfig

        fields = {f.name for f in dataclasses.fields(InfraConfig)}

        assert "minio_host" in fields
        assert "minio_port" in fields
        assert "minio_access_key" in fields
        assert "minio_secret_key" in fields

    def test_infra_config_has_qdrant_fields(self):
        """InfraConfig must have Qdrant configuration fields."""
        from core.config.infra_config import InfraConfig

        fields = {f.name for f in dataclasses.fields(InfraConfig)}

        assert "qdrant_host" in fields
        assert "qdrant_port" in fields

    def test_infra_config_has_redis_fields(self):
        """InfraConfig must have Redis configuration fields."""
        from core.config.infra_config import InfraConfig

        fields = {f.name for f in dataclasses.fields(InfraConfig)}

        assert "redis_host" in fields
        assert "redis_port" in fields
        assert "redis_db" in fields

    def test_infra_config_has_postgres_fields(self):
        """InfraConfig must have PostgreSQL configuration fields."""
        from core.config.infra_config import InfraConfig

        fields = {f.name for f in dataclasses.fields(InfraConfig)}

        assert "postgres_host" in fields
        assert "postgres_port" in fields

    def test_infra_config_has_neo4j_fields(self):
        """InfraConfig must have Neo4j configuration fields."""
        from core.config.infra_config import InfraConfig

        fields = {f.name for f in dataclasses.fields(InfraConfig)}

        assert "neo4j_host" in fields
        assert "neo4j_port" in fields

    def test_infra_config_default_values(self):
        """InfraConfig default values match expected."""
        from core.config.infra_config import InfraConfig

        config = InfraConfig()

        assert config.minio_grpc_host == "localhost"
        assert config.minio_grpc_port == 9000
        assert config.qdrant_grpc_host == "localhost"
        assert config.qdrant_grpc_port == 6333
        assert config.redis_grpc_host == "localhost"
        assert config.redis_grpc_port == 6379
        assert config.postgres_grpc_host == "localhost"
        assert config.postgres_grpc_port == 5432

    def test_infra_config_from_env_classmethod_exists(self):
        """InfraConfig must have from_env classmethod."""
        from core.config.infra_config import InfraConfig

        assert hasattr(InfraConfig, "from_env")
        assert callable(InfraConfig.from_env)


@pytest.mark.golden
class TestInfraConfigFromEnvGolden:
    """Golden tests for InfraConfig.from_env() - DO NOT MODIFY."""

    def test_from_env_returns_infra_config(self):
        """from_env() must return InfraConfig instance."""
        from core.config.infra_config import InfraConfig

        with patch.dict(os.environ, {}, clear=True):
            config = InfraConfig.from_env()

        assert isinstance(config, InfraConfig)

    def test_from_env_reads_qdrant_host(self):
        """from_env() reads QDRANT_HOST environment variable."""
        from core.config.infra_config import InfraConfig

        with patch.dict(os.environ, {"QDRANT_HOST": "qdrant.example.com"}, clear=True):
            config = InfraConfig.from_env()

        assert config.qdrant_grpc_host == "qdrant.example.com"

    def test_from_env_reads_qdrant_port(self):
        """from_env() reads QDRANT_PORT environment variable."""
        from core.config.infra_config import InfraConfig

        with patch.dict(os.environ, {"QDRANT_PORT": "6334"}, clear=True):
            config = InfraConfig.from_env()

        assert config.qdrant_grpc_port == 6334

    def test_from_env_reads_redis_config(self):
        """from_env() reads Redis configuration."""
        from core.config.infra_config import InfraConfig

        with patch.dict(
            os.environ,
            {"REDIS_HOST": "redis.example.com", "REDIS_PORT": "6379", "REDIS_DB": "1"},
            clear=True,
        ):
            config = InfraConfig.from_env()

        assert config.redis_grpc_host == "redis.example.com"
        assert config.redis_grpc_port == 6379
        assert config.redis_db == 1

    def test_from_env_reads_postgres_config(self):
        """from_env() reads PostgreSQL configuration."""
        from core.config.infra_config import InfraConfig

        with patch.dict(
            os.environ,
            {"POSTGRES_HOST": "pg.example.com", "POSTGRES_PORT": "5432"},
            clear=True,
        ):
            config = InfraConfig.from_env()

        assert config.postgres_grpc_host == "pg.example.com"
        assert config.postgres_grpc_port == 5432


@pytest.mark.golden
class TestConfigHelperFunctionsGolden:
    """Golden tests for config helper functions - DO NOT MODIFY."""

    def test_bool_helper_true_values(self):
        """_bool helper returns True for 'true'."""
        from core.config.mcp_config import _bool

        assert _bool("true") is True
        assert _bool("TRUE") is True
        assert _bool("True") is True

    def test_bool_helper_false_values(self):
        """_bool helper returns False for non-true values."""
        from core.config.mcp_config import _bool

        assert _bool("false") is False
        assert _bool("FALSE") is False
        assert _bool("0") is False
        assert _bool("") is False
        assert _bool("anything") is False

    def test_int_helper_valid_int(self):
        """_int helper parses valid integers."""
        from core.config.mcp_config import _int

        assert _int("123", 0) == 123
        assert _int("0", 99) == 0
        assert _int("-5", 0) == -5

    def test_int_helper_invalid_returns_default(self):
        """_int helper returns default for invalid input."""
        from core.config.mcp_config import _int

        assert _int("abc", 42) == 42
        assert _int("", 99) == 99
        assert _int("12.5", 0) == 0
