"""
Enums shared by models, Pydantic schemas, and the policy engine.

Kept in one file so a status name only ever needs to change in one place.
Using str-Enum (not a plain Python Enum) so these serialize cleanly to JSON
in API responses without extra encoder config.
"""

from enum import Enum


class MandateStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"       # soft-pause — see docs/architecture.md §0 (the USP)
    CANCELLED = "CANCELLED"  # terminal
    EXPIRED = "EXPIRED"      # terminal


class TransactionStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class PaymentType(str, Enum):
    RECURRING = "RECURRING"
    NEW = "NEW"


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class NotificationChannel(str, Enum):
    CONSOLE = "console"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
