"""Indiamart lead schemas"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, timezone
from enum import Enum
import uuid


class LeadStatus(str, Enum):
    NEW = "new"
    MESSAGE_SENT = "message_sent"
    MESSAGE_FAILED = "message_failed"
    FOLLOWED_UP = "followed_up"
    CONVERTED = "converted"
    CLOSED = "closed"


class LeadSource(str, Enum):
    INDIAMART = "indiamart"
    MANUAL = "manual"


class IndiamartLead(BaseModel):
    """Indiamart lead model"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    userId: str  # Which user this lead belongs to
    
    # Indiamart fields
    uniqueQueryId: str  # UNIQUE_QUERY_ID from Indiamart
    queryType: str  # W, B, P, BIZ, WA
    queryTime: str  # When lead was created on Indiamart
    
    # Sender (Buyer) info
    senderName: str
    senderMobile: str
    senderEmail: Optional[str] = None
    senderCompany: Optional[str] = None
    senderAddress: Optional[str] = None
    senderCity: Optional[str] = None
    senderState: Optional[str] = None
    senderPincode: Optional[str] = None
    senderCountry: str = "IN"
    
    # Query details
    subject: Optional[str] = None
    productName: Optional[str] = None
    queryMessage: Optional[str] = None
    categoryName: Optional[str] = None
    
    # Status tracking
    status: LeadStatus = LeadStatus.NEW
    source: LeadSource = LeadSource.INDIAMART
    
    # Message tracking
    messagesSent: int = 0
    lastMessageAt: Optional[str] = None
    lastMessageError: Optional[str] = None
    nextMessageAt: Optional[str] = None  # For recurring messages
    
    # Notes and follow-up
    notes: Optional[str] = None
    followUpDate: Optional[str] = None
    
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class IndiamartSettings(BaseModel):
    """User's Indiamart integration settings"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    userId: str
    
    # Webhook configuration
    isActive: bool = False
    webhookSecret: str = Field(default_factory=lambda: str(uuid.uuid4())[:16])
    
    # Auto-reply settings
    autoReplyEnabled: bool = True
    templateName: str = ""  # WhatsApp template name
    templateLanguage: str = "en_US"
    templateVariableCount: int = 1
    
    # Message content - variables available: {name}, {product}, {quantity}, {message}
    messageField1: str = ""  # Usually the main message
    messageField2: str = ""
    messageField3: str = ""
    messageField4: str = ""
    messageField5: str = ""
    
    # Timing
    sendDelay: int = 0  # Delay in minutes before sending (0 = immediate)
    
    # Recurring messages
    recurringEnabled: bool = False
    recurringIntervalHours: int = 24  # Hours between recurring messages
    recurringMaxCount: int = 3  # Max number of recurring messages
    recurringStopOnReply: bool = True  # Stop recurring if buyer replies
    
    # Header media (if needed)
    headerMediaType: str = "none"  # none, image, video, document
    headerImage: Optional[str] = None
    headerVideo: Optional[str] = None
    headerDocument: Optional[str] = None
    
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class IndiamartSettingsUpdate(BaseModel):
    """Update model for Indiamart settings"""
    isActive: Optional[bool] = None
    autoReplyEnabled: Optional[bool] = None
    templateName: Optional[str] = None
    templateLanguage: Optional[str] = None
    templateVariableCount: Optional[int] = None
    messageField1: Optional[str] = None
    messageField2: Optional[str] = None
    messageField3: Optional[str] = None
    messageField4: Optional[str] = None
    messageField5: Optional[str] = None
    sendDelay: Optional[int] = None
    recurringEnabled: Optional[bool] = None
    recurringIntervalHours: Optional[int] = None
    recurringMaxCount: Optional[int] = None
    recurringStopOnReply: Optional[bool] = None
    headerMediaType: Optional[str] = None
    headerImage: Optional[str] = None
    headerVideo: Optional[str] = None
    headerDocument: Optional[str] = None


class LeadUpdate(BaseModel):
    """Update model for leads"""
    status: Optional[LeadStatus] = None
    notes: Optional[str] = None
    followUpDate: Optional[str] = None
