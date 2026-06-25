from typing import List, Tuple
from .models import SignalDatapoint

class AnomalyDetector:
    def __init__(self):
        # Skeleton phase: purely dummy logic
        pass

    def detect_drift(self, tenant_id: str, signals: List[SignalDatapoint]) -> Tuple[bool, float, dict, str, float]:
        """
        Dummy logic for W11 AI engine skeleton.
        Returns hardcoded JSON matching the schema so CDO can integrate early.
        """
        # Hardcoded JSON đúng schema như yêu cầu trong capstone
        confidence = 0.85
        action = {
            "action_verb": "SCALE_UP",
            "target": f"{tenant_id} ECS Service",
            "from_to": "Current -> +2 Tasks",
            "evidence_link": f"https://dashboard.internal/metrics/{tenant_id}/cpu",
            "confidence": confidence
        }
        reasoning = "skeleton response"
        
        return True, 0.7, action, reasoning, confidence

