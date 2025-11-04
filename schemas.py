"""
Database Schemas for Velodent Chat & CRM Logging

Each Pydantic model below represents a MongoDB collection. The collection
name is the lowercase of the class name.

Examples:
- Lead -> "lead"
- Event -> "event"
- Transcript -> "transcript"
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr


class Lead(BaseModel):
    """Leads captured from the website chat widget or forms"""
    name: str = Field(..., description="Full name")
    email: Optional[EmailStr] = Field(None, description="Contact email")
    phone: Optional[str] = Field(None, description="Contact phone number")
    preferred_times: Optional[str] = Field(None, description="Preferred times or availability notes")
    intent: Optional[str] = Field(None, description="Primary user intent (booking, reschedule, insurance_check, payment_query, callback)")
    source: str = Field("website", description="Source of lead (e.g., website)")
    page: Optional[str] = Field(None, description="Page slug or URL where lead originated")
    session_id: Optional[str] = Field(None, description="Session identifier to link conversation")


class Event(BaseModel):
    """Events emitted by the chat widget for analytics and auditing"""
    event_type: str = Field(..., description="Event type (chat_started, lead_captured, booking_requested, insurance_check_requested, handoff_requested)")
    source: str = Field("website", description="Source such as website")
    page: Optional[str] = Field(None, description="Page slug or URL")
    session_id: Optional[str] = Field(None, description="Session identifier")
    payload: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional event data")


class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role: user or assistant")
    content: str = Field(..., description="Message text content")
    timestamp: Optional[str] = None


class Transcript(BaseModel):
    session_id: str = Field(..., description="Session identifier")
    lead_email: Optional[EmailStr] = None
    lead_phone: Optional[str] = None
    lead_name: Optional[str] = None
    page: Optional[str] = None
    messages: List[ChatMessage] = Field(default_factory=list, description="Ordered list of messages")
