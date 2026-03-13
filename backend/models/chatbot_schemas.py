"""Chatbot Lead Qualification - Pydantic models"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import uuid


class QuestionType(str, Enum):
    TEXT = "text"
    BUTTON = "button"
    LIST = "list"


class ConversationStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    FOLLOWUP_PENDING = "followup_pending"


class ChatbotLeadStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    UNQUALIFIED = "unqualified"


# ===== Category =====
class ChatbotCategory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    userId: str
    name: str
    description: Optional[str] = None
    triggerKeywords: List[str] = Field(default_factory=list)  # Keywords that trigger this category's flow
    employeePhone: Optional[str] = None  # Employee WhatsApp number for lead routing
    employeeName: Optional[str] = None
    isActive: bool = True
    sortOrder: int = 0
    createdAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updatedAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    triggerKeywords: List[str] = Field(default_factory=list)
    employeePhone: Optional[str] = None
    employeeName: Optional[str] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    triggerKeywords: Optional[List[str]] = None
    employeePhone: Optional[str] = None
    employeeName: Optional[str] = None
    isActive: Optional[bool] = None
    sortOrder: Optional[int] = None


# ===== Product =====
class ChatbotProduct(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    userId: str
    categoryId: str
    name: str
    description: Optional[str] = None
    price: Optional[str] = None
    isActive: bool = True
    createdAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updatedAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ProductCreate(BaseModel):
    categoryId: str
    name: str
    description: Optional[str] = None
    price: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[str] = None
    categoryId: Optional[str] = None
    isActive: Optional[bool] = None


# ===== Flow Question =====
class FlowQuestion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    userId: str
    categoryId: str
    questionText: str
    questionType: QuestionType = QuestionType.TEXT
    options: List[str] = Field(default_factory=list)  # For button/list type
    sortOrder: int = 0
    isRequired: bool = True
    createdAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class FlowQuestionCreate(BaseModel):
    categoryId: str
    questionText: str
    questionType: QuestionType = QuestionType.TEXT
    options: List[str] = Field(default_factory=list)
    sortOrder: int = 0
    isRequired: bool = True


class FlowQuestionUpdate(BaseModel):
    questionText: Optional[str] = None
    questionType: Optional[QuestionType] = None
    options: Optional[List[str]] = None
    sortOrder: Optional[int] = None
    isRequired: Optional[bool] = None


# ===== Chatbot Settings =====
class ChatbotSettings(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    userId: str
    isActive: bool = False
    greetingMessage: str = "Hello! Welcome. How can I help you today?"
    completionMessage: str = "Thank you! We have received your details. Our team will get back to you shortly."
    followUpDelayMinutes: int = 15
    maxFollowUps: int = 2
    followUpMessage: str = "Hi! We noticed you were looking at our products. Would you like to continue?"
    notifyMainNumber: bool = True
    mainNotifyPhone: Optional[str] = None  # Main user's WhatsApp for all notifications
    createdAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updatedAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ChatbotSettingsUpdate(BaseModel):
    isActive: Optional[bool] = None
    greetingMessage: Optional[str] = None
    completionMessage: Optional[str] = None
    followUpDelayMinutes: Optional[int] = None
    maxFollowUps: Optional[int] = None
    followUpMessage: Optional[str] = None
    notifyMainNumber: Optional[bool] = None
    mainNotifyPhone: Optional[str] = None


# ===== Conversation (Active chat sessions) =====
class ConversationAnswer(BaseModel):
    questionId: str
    questionText: str
    answer: str
    answeredAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ChatbotConversation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    userId: str  # The business user who owns this chatbot
    clientPhone: str  # The client's WhatsApp number
    clientName: Optional[str] = None
    status: ConversationStatus = ConversationStatus.ACTIVE
    categoryId: Optional[str] = None
    categoryName: Optional[str] = None
    productId: Optional[str] = None
    productName: Optional[str] = None
    currentStep: str = "greeting"  # greeting, category_select, product_search, product_select, question_0, question_1, ..., completed
    answers: List[ConversationAnswer] = Field(default_factory=list)
    followUpCount: int = 0
    nextFollowUpAt: Optional[str] = None
    lastMessageAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    createdAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updatedAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ===== Chatbot Lead (Completed conversations) =====
class ChatbotLead(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    userId: str
    conversationId: str
    clientPhone: str
    clientName: Optional[str] = None
    categoryId: Optional[str] = None
    categoryName: Optional[str] = None
    productId: Optional[str] = None
    productName: Optional[str] = None
    answers: List[ConversationAnswer] = Field(default_factory=list)
    status: ChatbotLeadStatus = ChatbotLeadStatus.NEW
    notes: Optional[str] = None
    notificationSent: bool = False
    employeeNotified: bool = False
    createdAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updatedAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class LeadStatusUpdate(BaseModel):
    status: Optional[ChatbotLeadStatus] = None
    notes: Optional[str] = None
