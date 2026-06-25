import uuid
import json
import os
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict

class AuditLogger:
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            
    def log_decision(self, tenant_id: str, request_data: Dict[str, Any], response_data: Dict[str, Any]) -> uuid.UUID:
        audit_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        
        # Hash input for traceability without storing raw PII
        signal_window_data = request_data.get("signal_window", [])
        input_hash = hashlib.sha256(json.dumps(signal_window_data, default=str).encode()).hexdigest()
        
        # 6 fields as required by Client spec
        log_entry = {
            "audit_id": str(audit_id),
            "timestamp": now.isoformat(),
            "tenant_id": tenant_id,
            "principal_id": request_data.get("principal_id", "unknown-principal"),
            "input_hash": input_hash,
            "recommendation_snapshot": response_data.get("recommendation", {})
        }
        
        log_path = os.path.join(self.log_dir, f"audit_{now.strftime('%Y%m%d')}.jsonl")
        with open(log_path, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
            
        return audit_id
