from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
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
    # Contract (ai-api-contract.md) maps invalid input -> 400 Bad Request (no retry).
    return JSONResponse(
        status_code=400,
        content={"detail": jsonable_encoder(exc.errors()), "body": jsonable_encoder(exc.body)},
    )

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "v1.0"}

@app.post("/v1/predict", response_model=PredictResponse)
async def predict_capacity(
    request: PredictRequest,
    x_tenant_id: str = Header(..., alias="X-Tenant-Id"),
    authorization: str = Header(..., alias="Authorization")
):
    # Multi-tenant isolation (ai-api-contract.md): labels.tenant_id must match the header.
    for dp in request.signal_window:
        label_tid = (dp.labels or {}).get("tenant_id")
        if label_tid is not None and label_tid != x_tenant_id:
            raise HTTPException(
                status_code=400,
                detail=f"tenant_id mismatch: labels.tenant_id={label_tid} != X-Tenant-Id={x_tenant_id}",
            )

    # Detect drift using STL-baseline + EWMA control chart
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
    }
    
    # Extract principal_id from authorization header (mocked for now, assumes role ARN or similar is passed)
    principal_id = authorization.split("Credential=")[-1].split("/")[0] if "Credential=" in authorization else "mock-principal-id"
    
    request_data = request.model_dump()
    request_data["principal_id"] = principal_id
    
    audit_id = audit_logger.log_decision(x_tenant_id, request_data, response_data)
    
    return PredictResponse(
        anomaly=anomaly,
        severity=severity,
        recommendation=suggested_action,
        reasoning=reasoning,
        audit_id=audit_id
    )
