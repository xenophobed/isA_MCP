#!/usr/bin/env python3
"""Business services configuration (HTTP/REST)

External service dependencies from isA_User and peer ISA services.
"""
import os
from dataclasses import dataclass

def _int(val: str, default: int) -> int:
    try:
        return int(val) if val else default
    except ValueError:
        return default

def _bool(val: str) -> bool:
    return val.lower() == "true"

@dataclass
class ServiceConfig:
    """All business HTTP service endpoints"""
    business_service_host: str = "localhost"

    # ===========================================
    # Peer ISA Services
    # ===========================================
    # isA_Model - LLM/Embedding service
    model_service_url: str = "http://localhost:8082"

    # isA_Agent - Agent orchestration
    agent_service_url: str = "http://localhost:8080"

    # isA_Data - RAG/Analytics service
    data_service_url: str = "http://localhost:8084"

    # isA_OS - Web/Cloud OS services
    web_service_url: str = "http://localhost:8083"
    os_service_url: str = "http://localhost:8085"

    # ===========================================
    # isA_User - Identity & Access Services
    # ===========================================
    auth_service_url: str = "http://localhost:8201"
    account_service_url: str = "http://localhost:8202"
    session_service_url: str = "http://localhost:8203"
    authorization_service_url: str = "http://localhost:8204"

    # ===========================================
    # isA_User - Audit & Notification
    # ===========================================
    audit_service_url: str = "http://localhost:8205"
    notification_service_url: str = "http://localhost:8206"

    # ===========================================
    # isA_User - Payment & Wallet
    # ===========================================
    payment_service_url: str = "http://localhost:8207"
    wallet_service_url: str = "http://localhost:8208"

    # ===========================================
    # isA_User - Storage & Order
    # ===========================================
    storage_service_url: str = "http://localhost:8209"
    order_service_url: str = "http://localhost:8210"

    # ===========================================
    # isA_User - Task & Organization
    # ===========================================
    task_service_url: str = "http://localhost:8211"
    organization_service_url: str = "http://localhost:8212"

    # ===========================================
    # isA_User - Invitation & Vault
    # ===========================================
    invitation_service_url: str = "http://localhost:8213"
    vault_service_url: str = "http://localhost:8214"

    # ===========================================
    # isA_User - Product & Billing
    # ===========================================
    product_service_url: str = "http://localhost:8215"
    billing_service_url: str = "http://localhost:8216"

    # ===========================================
    # isA_User - Calendar & Weather
    # ===========================================
    calendar_service_url: str = "http://localhost:8217"
    weather_service_url: str = "http://localhost:8218"

    # ===========================================
    # isA_User - Media & Device
    # ===========================================
    album_service_url: str = "http://localhost:8219"
    device_service_url: str = "http://localhost:8220"
    ota_service_url: str = "http://localhost:8221"
    media_service_url: str = "http://localhost:8222"

    # ===========================================
    # isA_User - AI/Memory
    # ===========================================
    memory_service_url: str = "http://localhost:8223"

    # ===========================================
    # isA_User - Telemetry & Event
    # ===========================================
    telemetry_service_url: str = "http://localhost:8225"
    event_service_url: str = "http://localhost:8230"

    # ===========================================
    # Service Discovery
    # ===========================================
    use_consul_discovery: bool = False

    @classmethod
    def from_env(cls) -> 'ServiceConfig':
        """Load service URLs from environment"""
        host = os.getenv("BUSINESS_SERVICE_HOST", "localhost")

        def _url(key: str, port: int) -> str:
            """Get service URL from env or construct from host:port"""
            url = os.getenv(key)
            return url if url else f"http://{host}:{port}"

        return cls(
            business_service_host=host,
            # Peer ISA Services
            model_service_url=os.getenv("MODEL_SERVICE_URL") or os.getenv("ISA_MODEL_URL", "http://localhost:8082"),
            agent_service_url=os.getenv("AGENT_SERVICE_URL", "http://localhost:8080"),
            data_service_url=os.getenv("DATA_SERVICE_URL", "http://localhost:8084"),
            web_service_url=os.getenv("WEB_SERVICE_URL", "http://localhost:8083"),
            os_service_url=os.getenv("OS_SERVICE_URL", "http://localhost:8085"),
            # isA_User Services
            auth_service_url=_url("AUTH_SERVICE_URL", 8201),
            account_service_url=_url("ACCOUNT_SERVICE_URL", 8202),
            session_service_url=_url("SESSION_SERVICE_URL", 8203),
            authorization_service_url=_url("AUTHORIZATION_SERVICE_URL", 8204),
            audit_service_url=_url("AUDIT_SERVICE_URL", 8205),
            notification_service_url=_url("NOTIFICATION_SERVICE_URL", 8206),
            payment_service_url=_url("PAYMENT_SERVICE_URL", 8207),
            wallet_service_url=_url("WALLET_SERVICE_URL", 8208),
            storage_service_url=_url("STORAGE_SERVICE_URL", 8209),
            order_service_url=_url("ORDER_SERVICE_URL", 8210),
            task_service_url=_url("TASK_SERVICE_URL", 8211),
            organization_service_url=_url("ORGANIZATION_SERVICE_URL", 8212),
            invitation_service_url=_url("INVITATION_SERVICE_URL", 8213),
            vault_service_url=_url("VAULT_SERVICE_URL", 8214),
            product_service_url=_url("PRODUCT_SERVICE_URL", 8215),
            billing_service_url=_url("BILLING_SERVICE_URL", 8216),
            calendar_service_url=_url("CALENDAR_SERVICE_URL", 8217),
            weather_service_url=_url("WEATHER_SERVICE_URL", 8218),
            album_service_url=_url("ALBUM_SERVICE_URL", 8219),
            device_service_url=_url("DEVICE_SERVICE_URL", 8220),
            ota_service_url=_url("OTA_SERVICE_URL", 8221),
            media_service_url=_url("MEDIA_SERVICE_URL", 8222),
            memory_service_url=_url("MEMORY_SERVICE_URL", 8223),
            telemetry_service_url=_url("TELEMETRY_SERVICE_URL", 8225),
            event_service_url=_url("EVENT_SERVICE_URL", 8230),
            # Service Discovery
            use_consul_discovery=_bool(os.getenv("USE_CONSUL_DISCOVERY", "false")),
        )
