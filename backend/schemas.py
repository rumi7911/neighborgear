"""Shared API/model validation without application or database side effects."""
from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Specification(BaseModel):
    model_config = ConfigDict(extra="forbid")
    equipment_type: Literal["walking_frame", "rollator"] | None = None
    min_height_cm: float | None = Field(None, ge=30, le=150)
    max_height_cm: float | None = Field(None, ge=30, le=150)
    user_weight_kg: float | None = Field(None, gt=0, le=500)
    needed_by: date | None = None
    return_by: date | None = None
    area: str | None = Field(None, max_length=100)
    window_start: str | None = Field(None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    window_end: str | None = Field(None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")


class CreateRequest(Specification):
    name: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=8000)


class Approval(BaseModel):
    equipment_id: str
    proposal_version: int = Field(ge=1)


class LifecycleEvent(BaseModel):
    type: Literal["cancel_driver", "confirm_delivery", "return_equipment", "pass_inspection", "fail_inspection"]
    driver_id: str | None = None


class ClockChange(BaseModel):
    days: int = Field(ge=1, le=30)
