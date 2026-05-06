from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, Text
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    
    # Profile fields
    age = Column(Float, nullable=True)
    gender = Column(String, nullable=True)
    ever_married = Column(String, nullable=True)
    work_type = Column(String, nullable=True)
    residence_type = Column(String, nullable=True)
    smoking_status = Column(String, nullable=True)
    heart_disease = Column(Integer, default=0)
    hypertension_history = Column(Integer, default=0)
    height = Column(Float, nullable=True)
    weight = Column(Float, nullable=True)
    bmi = Column(Float, nullable=True)

    # Exercise streak
    exercise_streak = Column(Integer, default=0)
    last_exercise_date = Column(Date, nullable=True)
    
    # Golden Hour tracking
    golden_hour_start = Column(String, nullable=True) # ISO Format string

    # Emergency contact
    emergency_phone = Column(String, nullable=True)

    records = relationship("HealthRecord", back_populates="owner")
    schedules = relationship("Schedule", back_populates="owner")


class HealthRecord(Base):
    __tablename__ = "health_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(Date, index=True)
    
    # Snapshot of user profile at time of entry
    age = Column(Float)
    gender = Column(String)
    ever_married = Column(String)
    work_type = Column(String)
    residence_type = Column(String)
    smoking_status = Column(String)
    systolic = Column(Integer)
    diastolic = Column(Integer)
    heart_disease = Column(Integer)
    avg_glucose_level = Column(Float)
    bmi = Column(Float)
    hypertension = Column(Integer, default=0)
    
    # FAST Symptoms (0=Không, 1=Nhẹ, 2=Rõ, 3=Nặng)
    fast_f = Column(Integer, default=0)
    fast_a = Column(Integer, default=0)
    fast_s = Column(Integer, default=0)
    fast_t = Column(Integer, default=0)
    
    # Results
    ml_score = Column(Integer)
    fast_sum = Column(Integer)
    combined_score = Column(Integer)
    final_score = Column(Integer)
    override_msg = Column(String, nullable=True)
    advice = Column(String, nullable=True)

    owner = relationship("User", back_populates="records")


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    schedule_type = Column(String, default="medication")  # medication | checkup
    date = Column(Date, nullable=False)
    time = Column(String, nullable=True)  # HH:MM format
    completed = Column(Integer, default=0)

    owner = relationship("User", back_populates="schedules")
