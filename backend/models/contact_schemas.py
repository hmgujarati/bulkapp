"""Contact and Auto-Message Models"""
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Optional, List
from datetime import datetime, timezone, date
from enum import Enum
import uuid


class ContactGroup(BaseModel):
    """Contact group for organizing contacts"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    userId: str
    name: str
    description: Optional[str] = None
    color: str = "#3B82F6"  # Default blue color
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Contact(BaseModel):
    """Contact with birthday and anniversary info"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    userId: str
    name: str
    email: Optional[str] = None
    phone: str  # Phone number with country code
    countryCode: str = "+91"  # Default country code
    dob: Optional[str] = None  # Date of birth (YYYY-MM-DD format)
    anniversary: Optional[str] = None  # Anniversary date (YYYY-MM-DD format)
    groupId: Optional[str] = None  # Reference to ContactGroup
    groupName: Optional[str] = None  # Denormalized for quick access
    notes: Optional[str] = None
    # Auto-message settings per contact
    sendBirthdayWish: bool = True
    sendAnniversaryWish: bool = True
    # Tracking
    lastBirthdayWishSent: Optional[str] = None  # Year of last wish sent
    lastAnniversaryWishSent: Optional[str] = None  # Year of last wish sent
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AutoMessageSettings(BaseModel):
    """User settings for automated birthday/anniversary messages"""
    model_config = ConfigDict(extra="ignore")
    userId: str
    # Default country code
    defaultCountryCode: str = "+91"
    # Birthday settings
    birthdayEnabled: bool = True
    birthdayTime: str = "09:00"  # Time to send (HH:MM in 24h format)
    birthdayTemplateName: str = ""  # Meta template name
    birthdayMessagePreview: str = "Happy Birthday {{name}}! Wishing you a wonderful day filled with joy and happiness!"
    # Anniversary settings
    anniversaryEnabled: bool = True
    anniversaryTime: str = "09:00"
    anniversaryTemplateName: str = ""
    anniversaryMessagePreview: str = "Happy Anniversary {{name}}! Wishing you many more years of love and happiness!"
    # Timezone
    timezone: str = "Asia/Kolkata"
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Request/Response models
class ContactGroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    color: str = "#3B82F6"


class ContactGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None


class ContactCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: str
    dob: Optional[str] = None  # YYYY-MM-DD
    anniversary: Optional[str] = None  # YYYY-MM-DD
    groupId: Optional[str] = None
    notes: Optional[str] = None
    sendBirthdayWish: bool = True
    sendAnniversaryWish: bool = True


class ContactUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    dob: Optional[str] = None
    anniversary: Optional[str] = None
    groupId: Optional[str] = None
    notes: Optional[str] = None
    sendBirthdayWish: Optional[bool] = None
    sendAnniversaryWish: Optional[bool] = None


class ContactBulkImport(BaseModel):
    contacts: List[ContactCreate]
    defaultCountryCode: str = "+91"


class AutoMessageSettingsUpdate(BaseModel):
    defaultCountryCode: Optional[str] = None
    birthdayEnabled: Optional[bool] = None
    birthdayTime: Optional[str] = None
    birthdayTemplateName: Optional[str] = None
    birthdayMessagePreview: Optional[str] = None
    anniversaryEnabled: Optional[bool] = None
    anniversaryTime: Optional[str] = None
    anniversaryTemplateName: Optional[str] = None
    anniversaryMessagePreview: Optional[str] = None
    timezone: Optional[str] = None
