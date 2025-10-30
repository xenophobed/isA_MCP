#!/usr/bin/env python3
"""Business services configuration (HTTP/REST)"""
import os
from dataclasses import dataclass

def _int(val: str, default: int) -> int:
    try:
        return int(val) if val else default
    except ValueError:
        return default

@dataclass
class ServiceConfig:
    """All business HTTP service endpoints"""
    business_service_host: str = "localhost"

    # Auth Services
    auth_service_url: str = "http://localhost:8201"
    account_service_url: str = "http://localhost:8202"
    session_service_url: str = "http://localhost:8203"
    authorization_service_url: str = "http://localhost:8204"

    # Audit & Notification
    audit_service_url: str = "http://localhost:8205"
    notification_service_url: str = "http://localhost:8206"

    # Payment & Wallet
    payment_service_url: str = "http://localhost:8207"
    wallet_service_url: str = "http://localhost:8208"

    # Storage & Order
    storage_service_url: str = "http://localhost:8209"
    order_service_url: str = "http://localhost:8210"

    # Task & Organization
    task_service_url: str = "http://localhost:8211"
    organization_service_url: str = "http://localhost:8212"

    # Invitation & Vault
    invitation_service_url: str = "http://localhost:8213"
    vault_service_url: str = "http://localhost:8214"

    # Product & Billing
    product_service_url: str = "http://localhost:8215"
    billing_service_url: str = "http://localhost:8216"

    # Calendar & Weather
    calendar_service_url: str = "http://localhost:8217"
    weather_service_url: str = "http://localhost:8218"

    # Media & Device
    album_service_url: str = "http://localhost:8219"
    device_service_url: str = "http://localhost:8220"
    ota_service_url: str = "http://localhost:8221"
    media_service_url: str = "http://localhost:8222"

    # Telemetry & Event
    telemetry_service_url: str = "http://localhost:8225"
    event_service_url: str = "http://localhost:8230"

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
            telemetry_service_url=_url("TELEMETRY_SERVICE_URL", 8225),
            event_service_url=_url("EVENT_SERVICE_URL", 8230)
        )
