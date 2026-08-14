from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.base import CallOutcome, FollowUpStatus, LeadSource, LeadStatus, LeadTemperature


class LeadCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    phone: str = Field(min_length=8, max_length=20)
    email: Optional[EmailStr] = None
    location: Optional[str] = None
    age: Optional[int] = Field(default=None, ge=10, le=80)
    course_id: Optional[UUID] = None
    source: LeadSource
    notes: Optional[str] = None
    message: Optional[str] = None
    auto_assign: bool = False


class WebsiteEnquiry(BaseModel):
    name: str
    phone: str
    email: Optional[EmailStr] = None
    course: Optional[str] = None
    message: Optional[str] = None


class LeadAssign(BaseModel):
    staff_id: UUID
    notes: Optional[str] = None


class CallActivityCreate(BaseModel):
    call_outcome: CallOutcome
    temperature: Optional[LeadTemperature] = None
    feedback: Optional[str] = None
    duration_seconds: Optional[int] = Field(default=None, ge=0)
    next_follow_up_at: Optional[datetime] = None
    not_interested: bool = False


class LeadUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    location: Optional[str] = None
    age: Optional[int] = None
    course_id: Optional[UUID] = None
    status: Optional[LeadStatus] = None
    temperature: Optional[LeadTemperature] = None
    notes: Optional[str] = None
    parent_involved: Optional[bool] = None
    asked_about_admission: Optional[bool] = None
    requested_brochure: Optional[bool] = None
    attended_counselling: Optional[bool] = None
    campus_visit_done: Optional[bool] = None
    registration_discussion: Optional[bool] = None


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_code: str
    name: str
    phone: str
    email: Optional[str] = None
    location: Optional[str] = None
    age: Optional[int] = None
    course_id: Optional[UUID] = None
    source: LeadSource
    assigned_staff_id: Optional[UUID] = None
    temperature: Optional[LeadTemperature] = None
    status: LeadStatus
    score: int
    notes: Optional[str] = None
    last_contacted_at: Optional[datetime] = None
    next_follow_up_at: Optional[datetime] = None
    created_at: datetime
    parent_involved: bool = False
    asked_about_admission: bool = False
    requested_brochure: bool = False
    attended_counselling: bool = False
    campus_visit_done: bool = False
    registration_discussion: bool = False


class LeadActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    activity_type: str
    call_outcome: Optional[CallOutcome] = None
    duration_seconds: Optional[int] = None
    temperature: Optional[LeadTemperature] = None
    feedback: Optional[str] = None
    created_at: datetime


class FollowUpOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_id: UUID
    staff_id: UUID
    scheduled_at: datetime
    status: FollowUpStatus
    notes: Optional[str] = None
    completed_at: Optional[datetime] = None


class LeadDetailOut(LeadOut):
    activities: list[LeadActivityOut] = []
    followups: list[FollowUpOut] = []
    assigned_staff_name: Optional[str] = None
    course_name: Optional[str] = None
    duplicates: list[LeadOut] = []
