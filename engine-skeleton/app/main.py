from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from typing import Optional

from .models import PredictRequest, PredictResponse
from .engine import AnomalyDetector
from .audit import AuditLogger

app = FastAPI(title="Foresight Lens AI Engine", version="v1.0")
detector = AnomalyDetector()
audit_logger = AuditLogger()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )

@app.post("/v1/predict", response_model=PredictResponse)
async def predict_capacity(
    request: PredictRequest,
    x_tenant_id: str = Header(..., alias="X-Tenant-Id"),
    authorization: str = Header(..., alias="Authorization")
):
    # Detect drift using 3-sigma engine
    anomaly, severity, suggested_action, reasoning, confidence = detector.detect_drift(
        tenant_id=x_tenant_id,
        signals=request.signal_window
    )
    
    # Audit log
    response_data = {
        "anomaly": anomaly,
        "severity": severity,
        "recommendation": suggested_action,
        "reasoning": reasoning,
        "confidence": confidence
    }
    
    audit_id = audit_logger.log_decision(x_tenant_id, request.model_dump(), response_data)
    
    return PredictResponse(
        anomaly=anomaly,
        severity=severity,
        recommendation=suggested_action,
        reasoning=reasoning,
        confidence=confidence,
        audit_id=audit_id
    )
