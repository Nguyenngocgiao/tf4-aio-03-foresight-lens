import re

with open('/home/dinh/Downloads/tf4-aio-03/docs/03_ai_engine_spec.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace Section 4
s4_pattern = r'## 4\. Prompt engineering / RAG strategy.*?## 5\. AI Model Governance'
s4_repl = '''## 4. Prompt engineering / RAG strategy

*N/A — Hệ thống sử dụng Thuật toán Thống kê (Statistical Model) thay vì LLM. Không có Prompt, Context Window hay RAG Pipeline.*

## 5. AI Model Governance'''
content = re.sub(s4_pattern, s4_repl, content, flags=re.DOTALL)

# Replace mechanisms
mech_pattern = r'\| Mechanism \| Implementation \| Layer \|.*?\| Eval baseline check \| Weekly re-run eval set, alert nếu metric drop >10% \| CI/CD job \|'
mech_repl = '''| Mechanism | Implementation | Layer |
|---|---|---|
| Input sanitization | Pydantic Schema Validation (reject if invalid schema/type) | API Layer |
| Output schema validation | JSON schema enforce, reject if invalid | Post-Processing |
| Confidence threshold | App-level: confidence < 0.6 → `INVESTIGATE` | App layer |
| Audit log mandatory | Cannot return response without audit entry | App layer |
| Per-tenant isolation | Context isolation via `tenant_id` header | App layer |
| Rate limit | API Gateway usage plan per tenant | Edge |
| Circuit breaker | API threshold 60%+ error → fallback rule-based | App layer |
| Eval baseline check | Scheduled re-run eval set, alert nếu metrics drop | CI/CD job |'''
content = re.sub(mech_pattern, mech_repl, content, flags=re.DOTALL)

# Replace NFR Matrix
nfr_pattern = r'\| NFR ID \| Category \| Requirement \| Control \| Evidence \| Owner \|.*?\| MG-10 \| Safety \| Drift threshold \+ retrain trigger config \(only if model self-trained\) \| Drift baseline \+ retrain ADR \| Drift detection log \| Nhóm AI \|'
nfr_repl = '''| NFR ID | Category | Requirement | Control | Evidence | Owner |
|---|---|---|---|---|---|
| MG-01 | Governance | Decision explainable | `reasoning` field ≤300 chars per output | Sample output | Nhóm AI |
| MG-02 | Governance | Audit complete | 100% AI calls audited | Audit log query | Nhóm AI |
| MG-03 | Governance | Confidence gating | Action requires confidence ≥ 0.6 | Code review + test | Nhóm AI |
| MG-04 | Performance | P99 latency < 500ms | Latency monitor | CloudWatch dashboard | Nhóm AI |
| MG-05 | Cost | Cost control (< $200) | No LLM calls, compute only | Quota config | Nhóm AI |
| MG-06 | Reliability | Fallback to rule-based on Engine failure | Circuit breaker code / 503 HTTP | Chaos test | Nhóm AI |
| MG-07 | Compliance | No PII data logging | Data hashing before log | Audit log scan | Nhóm AI |
| MG-08 | Drift | Eval baseline check | Scheduled eval job | CI/CD run history | Nhóm AI |
| MG-09 | Safety | Closed-loop verify post-action (CDO calls /v1/verify) | Verify metric check API | Action audit log | Nhóm AI |
| MG-10 | Safety | Threshold tuning / retrain | Statistical baseline recalculation | Drift detection log | Nhóm AI |'''
content = re.sub(nfr_pattern, nfr_repl, content, flags=re.DOTALL)

# Replace Section 6
s6_pattern = r'## 6\. AI Security.*?## 7\. Eval methodology'
s6_repl = '''## 6. Statistical Engine Security (Thay thế AI Security)

*Vì hệ thống sử dụng thuật toán Thống kê thay vì LLM, các rủi ro truyền thống của GenAI (Prompt Injection, Jailbreaking, Hallucination, Training Poisoning) được **loại trừ hoàn toàn** theo thiết kế (Security-by-design).*

Các rủi ro bảo mật tập trung vào tầng API và dữ liệu:

### 6.1 Security Risks (Overview)

| Risk | Description | Severity | Mitigation Layer |
|---|---|---|---|
| **Data Bleed (Cross-tenant)** | Dữ liệu tenant A rò rỉ sang tenant B khi tính baseline | High | Code level: Context parsing luôn group theo `X-Tenant-Id`. |
| **Denial of Service (DoS)** | Gửi mảng `signal_window` quá lớn gây cạn kiệt CPU/memory | Medium | Pydantic: Limit size của mảng input `signal_window`. |
| **Data Poisoning** | CDO gửi sai metric giả để phá baseline | Low | Authentication via IAM SigV4, chỉ CDO system identity có quyền gọi API. |
| **PII Leakage in Logs** | Lưu lọt PII vào Audit Log | Medium | Hash toàn bộ request body (`input_hash`) thay vì lưu raw payload. |

### 6.2 Data Input Validation

| Control | Description |
|---|---|
| Schema validation | Strict Pydantic JSON schema, reject invalid payload (`HTTP 422`). |
| Data type checks | `value` bắt buộc là `float`, `ts` bắt buộc `RFC3339`. |
| Context Isolation | `X-Tenant-Id` header bắt buộc. Không có header → `HTTP 422`. |

### 6.3 Security Audit Trail

Toàn bộ payload nhạy cảm không được lưu thô, mà dùng Hashing (SHA-256) để verify tính toàn vẹn và chống lộ PII:
```json
{
  "ts": "2026-06-25T10:30:00Z",
  "correlation_id": "req-1234",
  "tenant_id": "tnt-abc",
  "model_version": "tf4-3sigma-rolling-v1",
  "input_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "data_encryption": "AWS KMS CMK",
  "decision": "SCALE_UP",
  "confidence": 1.0,
  "execution_ms": 5.42
}
```

## 7. Eval methodology'''
content = re.sub(s6_pattern, s6_repl, content, flags=re.DOTALL)

with open('/home/dinh/Downloads/tf4-aio-03/docs/03_ai_engine_spec.md', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
