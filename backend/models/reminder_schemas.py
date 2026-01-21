"""Reminder Bot Models"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, timezone
from enum import Enum
import uuid


class ReminderStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Reminder Number - phone numbers that can receive reminders
class ReminderNumber(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    userId: str
    phone: str  # Phone number with country code
    name: str  # Contact name
    timezone: str = "Asia/Kolkata"  # Default timezone
    isDefault: bool = False  # Is this the user's own number
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReminderNumberCreate(BaseModel):
    phone: str
    name: str
    timezone: str = "Asia/Kolkata"
    isDefault: bool = False


class ReminderNumberUpdate(BaseModel):
    name: Optional[str] = None
    timezone: Optional[str] = None
    isDefault: Optional[bool] = None


# Reminder - the actual reminder
class Reminder(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    userId: str
    numberId: str  # Reference to ReminderNumber
    phone: str  # Denormalized for quick access
    contactName: str  # Denormalized
    title: str  # Short title/summary
    message: str  # Full reminder message
    originalInput: str  # The natural language input from user
    scheduledAt: datetime  # When to send the reminder
    timezone: str  # Timezone of the scheduled time
    status: ReminderStatus = ReminderStatus.PENDING
    # Meta template settings
    useTemplate: bool = True  # Use pre-approved template
    templateId: Optional[str] = None  # Meta template ID if using template
    # Delivery info
    sentAt: Optional[datetime] = None
    messageId: Optional[str] = None
    error: Optional[str] = None
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReminderCreate(BaseModel):
    numberId: str  # Which number to send to
    naturalLanguageInput: str  # e.g., "remind me to call Harsh at 10 am tomorrow"
    useTemplate: bool = True
    templateId: Optional[str] = None


class ReminderCreateDirect(BaseModel):
    """Direct reminder creation without NLP parsing"""
    numberId: str
    title: str
    message: str
    scheduledAt: datetime
    useTemplate: bool = True
    templateId: Optional[str] = None


class ReminderUpdate(BaseModel):
    title: Optional[str] = None
    message: Optional[str] = None
    scheduledAt: Optional[datetime] = None
    useTemplate: Optional[bool] = None
    templateId: Optional[str] = None


# User settings for reminders
class ReminderSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    userId: str
    openaiApiKey: Optional[str] = None  # User's OpenAI API key
    defaultTemplateId: Optional[str] = None  # Default Meta template for reminders
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReminderSettingsUpdate(BaseModel):
    openaiApiKey: Optional[str] = None
    defaultTemplateId: Optional[str] = None


# NLP Parse Response
class ParsedReminder(BaseModel):
    title: str
    message: str
    scheduledAt: datetime
    confidence: float  # How confident the AI is in the parsing
