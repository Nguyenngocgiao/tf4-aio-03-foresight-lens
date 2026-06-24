from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

class TimeRange(BaseModel):
    start_ts: datetime
    end_ts: datetime

class PredictContext(BaseModel):
    deployment_version: str
    time_range: TimeRange

class SignalDatapoint(BaseModel):
    ts: datetime
    signal_name: str
    value: float
    labels: Optional[Dict[str, Any]] = None

class PredictRequest(BaseModel):
    signal_window: List[SignalDatapoint]
    context: PredictContext
    
    @field_validator('signal_window')
    @classmethod
    def check_window_size(cls, v: List[SignalDatapoint]) -> List[SignalDatapoint]:
        if len(v) < 60:
            raise ValueError('signal_window BẮT BUỘC phải chứa ≥ 60 datapoints (60 phút).')
        return v

class Recommendation(BaseModel):
    action_verb: str     # e.g., "SCALE_UP", "ROLLBACK", "RESTART"
    target: str          # e.g., "payment-gw ECS Service"
    from_to: str         # e.g., "3 tasks -> 5 tasks"
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_link: str   # e.g., "https://dashboard.internal/metrics/..."

class PredictResponse(BaseModel):
    anomaly: bool
    severity: float = Field(ge=0.0, le=1.0)
    recommendation: Optional[Recommendation] = None
    reasoning: str = Field(max_length=300)
    audit_id: uuid.UUID
