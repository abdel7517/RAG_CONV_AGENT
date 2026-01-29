"""Ports (interfaces abstraites) du backend."""
from backend.domain.ports.event_broker_port import EventBrokerPort, Subscription

__all__ = ["EventBrokerPort", "Subscription"]
