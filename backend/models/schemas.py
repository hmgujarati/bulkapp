"""Pydantic models and schemas"""
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import uuid


class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"


class CampaignStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    SCHEDULED = "scheduled"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class MessageStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DELIVERED = "delivered"


# User Models
class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    firstName: str
    lastName: str
    role: Role = Role.USER
    bizChatToken: Optional[str] = None
    bizChatVendorUID: Optional[str] = None
    dailyLimit: int = 1000
    dailyUsage: int = 0
    lastResetDateTime: Optional[str] = None  # Full ISO datetime for 24-hour reset
    isPaused: bool = False
    # Feature access control - which features this user can access
    features: dict = Field(default_factory=lambda: {
        "bulk_messages": True,
        "reminders": True,
        "contacts": True,
        "templates": True,
        "campaigns": True,
        "indiamart": False  # New feature - disabled by default
    })
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    firstName: str
    lastName: str
    role: Optional[Role] = Role.USER


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    bizChatToken: Optional[str] = None
    bizChatVendorUID: Optional[str] = None


class PasswordChange(BaseModel):
    currentPassword: str
    newPassword: str


class UserPauseUpdate(BaseModel):
    isPaused: bool


class UserLimitUpdate(BaseModel):
    dailyLimit: int


class TokenData(BaseModel):
    userId: str
    email: str
    role: Role


# Campaign Models
class RecipientInfo(BaseModel):
    phone: str
    name: str
    status: MessageStatus = MessageStatus.PENDING
    messageId: Optional[str] = None
    error: Optional[str] = None
    sentAt: Optional[datetime] = None


class Campaign(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    userId: str
    name: str
    templateName: str
    recipients: List[RecipientInfo]
    totalCount: int
    sentCount: int = 0
    failedCount: int = 0
    pendingCount: int
    scheduledAt: Optional[datetime] = None
    status: CampaignStatus = CampaignStatus.PENDING
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completedAt: Optional[datetime] = None


class SendMessageRequest(BaseModel):
    recipients: List[Dict[str, str]]
    templateName: str
    campaignName: str
    countryCode: Optional[str] = None
    scheduledAt: Optional[datetime] = None
    templateParameters: Optional[Dict[str, Any]] = None
    # Media headers
    header_image: Optional[str] = None
    header_video: Optional[str] = None
    header_document: Optional[str] = None
    header_document_name: Optional[str] = None
    header_field_1: Optional[str] = None
    # Location data
    location_latitude: Optional[str] = None
    location_longitude: Optional[str] = None
    location_name: Optional[str] = None
    location_address: Optional[str] = None


# Template Models
class SavedTemplate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    userId: str
    name: str
    templateName: str
    templateLanguage: str = "en"
    field1: Optional[str] = None
    field2: Optional[str] = None
    field3: Optional[str] = None
    field4: Optional[str] = None
    field5: Optional[str] = None
    # Media fields
    header_image: Optional[str] = None
    header_video: Optional[str] = None
    header_document: Optional[str] = None
    header_document_name: Optional[str] = None
    header_field_1: Optional[str] = None
    # Location fields
    location_latitude: Optional[str] = None
    location_longitude: Optional[str] = None
    location_name: Optional[str] = None
    location_address: Optional[str] = None
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SavedTemplateCreate(BaseModel):
    name: str
    templateName: str
    templateLanguage: str = "en"
    field1: Optional[str] = None
    field2: Optional[str] = None
    field3: Optional[str] = None
    field4: Optional[str] = None
    field5: Optional[str] = None
    # Media fields
    header_image: Optional[str] = None
    header_video: Optional[str] = None
    header_document: Optional[str] = None
    header_document_name: Optional[str] = None
    header_field_1: Optional[str] = None
    # Location fields
    location_latitude: Optional[str] = None
    location_longitude: Optional[str] = None
    location_name: Optional[str] = None
    location_address: Optional[str] = None


class TemplateParameter(BaseModel):
    type: str = "text"
    text: str
