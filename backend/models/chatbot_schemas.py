"""Chatbot Lead Flow - Simplified Pydantic models"""
from pydantic import BaseModel, Field
from typing import List, Optional
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


# ===== Flow Question (embedded in Flow) =====
class FlowQuestionItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    questionText: str
    questionType: QuestionType = QuestionType.TEXT
    options: List[str] = Field(default_factory=list)


class FlowQuestionInput(BaseModel):
    questionText: str
    questionType: QuestionType = QuestionType.TEXT
    options: List[str] = Field(default_factory=list)


# ===== Chatbot Flow =====
class ChatbotFlow(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    userId: str
    name: str
    triggerKeywords: List[str] = Field(default_factory=list)
    greetingMessage: Optional[str] = None
    completionMessage: str = "Thank you! We have received your details. Our team will get back to you shortly."
    questions: List[FlowQuestionItem] = Field(default_factory=list)
    notifyPhone: Optional[str] = None
    isActive: bool = True
    createdAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updatedAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class FlowCreate(BaseModel):
    name: str
    triggerKeywords: List[str] = Field(default_factory=list)
    greetingMessage: Optional[str] = None
    completionMessage: str = "Thank you! We have received your details. Our team will get back to you shortly."
    questions: List[FlowQuestionInput] = Field(default_factory=list)
    notifyPhone: Optional[str] = None


class FlowUpdate(BaseModel):
    name: Optional[str] = None
    triggerKeywords: Optional[List[str]] = None
    greetingMessage: Optional[str] = None
    completionMessage: Optional[str] = None
    questions: Optional[List[FlowQuestionInput]] = None
    notifyPhone: Optional[str] = None
    isActive: Optional[bool] = None


# ===== Chatbot Settings (global) =====
class ChatbotSettings(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    userId: str
    isActive: bool = False
    defaultNotifyPhone: Optional[str] = None
    followUpDelayMinutes: int = 15
    maxFollowUps: int = 2
    followUpMessage: str = "Hi! We noticed you were interested. Would you like to continue?"
    createdAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updatedAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ChatbotSettingsUpdate(BaseModel):
    isActive: Optional[bool] = None
    defaultNotifyPhone: Optional[str] = None
    followUpDelayMinutes: Optional[int] = None
    maxFollowUps: Optional[int] = None
    followUpMessage: Optional[str] = None


# ===== Conversation (Active chat session) =====
class ConversationAnswer(BaseModel):
    questionId: str
    questionText: str
    answer: str
    answeredAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ChatbotConversation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    userId: str
    flowId: str
    flowName: str
    clientPhone: str
    clientName: Optional[str] = None
    status: ConversationStatus = ConversationStatus.ACTIVE
    currentStep: int = 0  # Index of current question (0-based)
    answers: List[ConversationAnswer] = Field(default_factory=list)
    followUpCount: int = 0
    nextFollowUpAt: Optional[str] = None
    lastMessageAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    createdAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updatedAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ===== Lead (Completed conversation) =====
class ChatbotLead(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    userId: str
    conversationId: str
    flowId: str
    flowName: str
    clientPhone: str
    clientName: Optional[str] = None
    answers: List[ConversationAnswer] = Field(default_factory=list)
    status: ChatbotLeadStatus = ChatbotLeadStatus.NEW
    notes: Optional[str] = None
    notificationSent: bool = False
    createdAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updatedAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class LeadStatusUpdate(BaseModel):
    status: Optional[ChatbotLeadStatus] = None
    notes: Optional[str] = None
