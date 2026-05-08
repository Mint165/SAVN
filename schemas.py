import datetime
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


GENDER_VALUES = {"Male", "Female", "Other"}
MARRIED_VALUES = {"Yes", "No"}
RESIDENCE_VALUES = {"Urban", "Rural"}
WORK_TYPE_VALUES = {"Private", "Self-employed", "Govt_job", "children", "Never_worked"}
SMOKING_VALUES = {"never smoked", "formerly smoked", "smokes", "Unknown"}
SCHEDULE_TYPE_VALUES = {"medication", "checkup"}
PHONE_PATTERN = re.compile(r"^[0-9+\-\s()]{8,20}$")


def _empty_to_none(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
    return value


def _checkbox_to_int(value) -> int:
    if value in (None, "", 0, "0", False):
        return 0
    if isinstance(value, str):
        return 1 if value.strip().lower() in {"1", "true", "on", "yes"} else 0
    return 1 if value else 0


class BaseFormModel(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


class LoginPayload(BaseFormModel):
    action: Literal["login", "register"]
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)
    age: float | None = Field(default=None, ge=1, le=120)
    gender: Literal["Male", "Female", "Other"] | None = None
    work_type: Literal["Private", "Self-employed", "Govt_job", "children", "Never_worked"] | None = None
    ever_married: Literal["Yes", "No"] | None = None
    residence_type: Literal["Urban", "Rural"] | None = None
    smoking_status: Literal["never smoked", "formerly smoked", "smokes", "Unknown"] | None = None
    heart_disease: int = 0
    hypertension_history: int = 0
    bmi: float | None = Field(default=None, ge=10, le=60)

    @field_validator("heart_disease", "hypertension_history", mode="before")
    @classmethod
    def normalize_checkbox(cls, value):
        return _checkbox_to_int(value)

    @model_validator(mode="after")
    def validate_register_fields(self):
        if self.action != "register":
            return self

        if len(self.password) < 6:
            raise ValueError("Password must be at least 6 characters long.")

        required_fields = {
            "age": self.age,
            "gender": self.gender,
            "work_type": self.work_type,
            "ever_married": self.ever_married,
            "residence_type": self.residence_type,
            "smoking_status": self.smoking_status,
            "bmi": self.bmi,
        }
        missing = [name for name, value in required_fields.items() if value is None]
        if missing:
            raise ValueError("Missing required registration fields.")
        return self


class ProfilePayload(BaseFormModel):
    age: float = Field(ge=1, le=120)
    gender: Literal["Male", "Female", "Other"]
    work_type: Literal["Private", "Self-employed", "Govt_job", "children", "Never_worked"]
    ever_married: Literal["Yes", "No"]
    residence_type: Literal["Urban", "Rural"]
    smoking_status: Literal["never smoked", "formerly smoked", "smokes", "Unknown"]
    heart_disease: int = 0
    hypertension_history: int = 0
    bmi: float = Field(ge=10, le=60)
    emergency_phone: str | None = Field(default=None, max_length=20)

    @field_validator("heart_disease", "hypertension_history", mode="before")
    @classmethod
    def normalize_checkbox(cls, value):
        return _checkbox_to_int(value)

    @field_validator("emergency_phone", mode="before")
    @classmethod
    def normalize_phone(cls, value):
        return _empty_to_none(value)

    @field_validator("emergency_phone")
    @classmethod
    def validate_phone(cls, value):
        if value is None:
            return None
        if not PHONE_PATTERN.match(value):
            raise ValueError("Emergency phone format is invalid.")
        return value


class DailyRecordPayload(BaseFormModel):
    systolic: int = Field(ge=60, le=250)
    diastolic: int = Field(ge=40, le=150)
    avg_glucose_level: float | None = Field(default=None, ge=40, le=600)
    fast_f: int = Field(default=0, ge=0, le=3)
    fast_a: int = Field(default=0, ge=0, le=3)
    fast_s: int = Field(default=0, ge=0, le=3)
    fast_t: int = Field(default=0, ge=0, le=3)
    record_date: datetime.date

    @field_validator("avg_glucose_level", mode="before")
    @classmethod
    def normalize_optional_float(cls, value):
        return _empty_to_none(value)


class SchedulePayload(BaseFormModel):
    title: str = Field(min_length=1, max_length=120)
    schedule_type: Literal["medication", "checkup"]
    date: datetime.date
    time: str | None = None
    description: str | None = Field(default=None, max_length=300)

    @field_validator("time", "description", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        return _empty_to_none(value)

    @field_validator("time")
    @classmethod
    def validate_time(cls, value):
        if value is None:
            return None
        datetime.datetime.strptime(value, "%H:%M")
        return value


class ScheduleDeletePayload(BaseModel):
    schedule_id: int = Field(gt=0)


class ExerciseCompletePayload(BaseModel):
    model_config = ConfigDict(extra="ignore")


class LogoutPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")


class TriggerGoldenHourPayload(BaseModel):
    source: Literal["face", "speech", "manual"] = "manual"
