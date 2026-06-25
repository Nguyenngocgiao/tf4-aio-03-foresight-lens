from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from typing import Optional
import uuid

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
        content={"detail": jsonable_encoder(exc.errors()), "body": jsonable_encoder(exc.body)},
    )

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "v1.0"}

@app.post("/v1/predict", response_model=PredictResponse)
async def predict_capacity(
    request: PredictRequest,
    x_tenant_id: str = Header(..., alias="X-Tenant-Id"),
    authorization: str = Header(..., alias="Authorization"),
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-Id")
):
    if not x_correlation_id:
        x_correlation_id = str(uuid.uuid4())

    # Validate tenant isolation
    for dp in request.signal_window:
        if dp.labels and dp.labels.get("tenant_id") and dp.labels.get("tenant_id") != x_tenant_id:
            raise HTTPException(status_code=400, detail="Tenant ID in labels does not match X-Tenant-Id header")

    # Detect drift using ewma_stl engine
    anomaly, severity, suggested_action, reasoning, confidence = detector.detect_drift(
        tenant_id=x_tenant_id,
        signals=request.signal_window
    )
    
    # Confidence gating MG-03
    if suggested_action and confidence < 0.7:
        suggested_action["action_verb"] = "INVESTIGATE"

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
