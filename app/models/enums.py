"""Shared string enums used across models and schemas."""
import enum


class Role(str, enum.Enum):
    admin = "admin"
    manager = "manager"
    csm = "csm"


class CustomerStatus(str, enum.Enum):
    prospect = "prospect"
    active = "active"
    at_risk = "at_risk"
    churned = "churned"


class InteractionType(str, enum.Enum):
    meeting = "meeting"
    call = "call"
    email = "email"
    note = "note"


class Sentiment(str, enum.Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"


class InsightStatus(str, enum.Enum):
    success = "success"
    fallback = "fallback"
