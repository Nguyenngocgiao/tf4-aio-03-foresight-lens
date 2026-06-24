# AI Engine Spec - Foresight Lens

<!-- Doc owner: AIO-03
     Status: Draft (W11 T3-T4) → Final (W11 T6 Pack #1) → Updated (W12 T4 Pack #2)
     Word target: 2500-4000 từ (Heavy tier)
     Reference: TCB DAB Framework - AI Model Governance + AI Security (adapted for capstone) -->

> **📌 Capstone scope guide** - 9 sections không phải tất cả "must-deploy", một số "design-only":
>
> **Pack #1 (EOD T6 W11) minimum**: Sections 1, 2, 3, 4 (skeleton) + 5.1-5.3 + 6.1, 6.2.1, 6.2.2 (skeleton) + 7 (skeleton) + 8 (forecast) + 9
>
> **Pack #2 (EOD T4 W12) full**: TẤT CẢ sections refined với:
> - 5.5 Model NFR Control Matrix có MG-01..MG-08 evidence
> - 6 AI Security với Bedrock Guardrails configured (NOT just spec)
> - 7 Eval với real measured numbers
> - 8 Cost với actual measured
>
> **Design-only OK cho capstone** (note rõ trong doc nếu áp dụng): 6.6 LLM for AI Agents (nếu không dùng agentic) · 6.4 Training Model Security (capstone dùng foundation model)

## 1. Model architecture

- **Pattern chọn**: Statistical Analysis Engine (EWMA & STL Decomposition Rolling Window) thay vì LLM.
- **Lý do**: Đáp ứng chính xác bài toán phát hiện bất thường (Anomaly Detection) cho Time-series data. Dựa trên bằng chứng thống kê (ANOVA, Kruskal-Wallis), phương pháp này phát hiện Capacity Exhaustion với Lead Time > 100 phút, vượt yêu cầu 15 phút. Khả năng cô lập nhiễu với False Positive < 1%.
- **Alternatives rejected**: LLM / Agentic. Bị reject vì latency cao, tốn kém (Cost), và không phù hợp với bản chất dữ liệu chuỗi thời gian (cần tính toán số học chính xác thay vì sinh text).

## 2. Model selection

| Field | Value |
|---|---|
| Provider | Python / NumPy (In-house) |
| Model ID | `tf4-ewma-stl-v1` |
| Region | All regions (Deploy as container) |
| Context window | 1000 data points (Rolling Window) |
| Cost/1k input tokens | $0 (Local execution) |
| Cost/1k output tokens | $0 (Local execution) |
| Estimated per-call cost | ~$0.000001 (Compute only) |

## 3. Multi-tenant routing

<!-- Làm sao đảm bảo tenant A's data không leak sang tenant B? -->

- **Tenant identification**: `tenant_id` từ JWT / header X-Tenant-Id
- **Context isolation**: per-request scoping - không persist context across tenants
- **State storage**: per-tenant partition (DynamoDB pk = tenant_id, or RDS schema)
- **Audit log**: every AI call → audit entry với `tenant_id`

## 4. Prompt engineering / RAG strategy

*N/A — Hệ thống sử dụng Thuật toán Thống kê (Statistical Model) thay vì LLM. Không có Prompt, Context Window hay RAG Pipeline.*

## 5. AI Model Governance

### 5.1 Governance Objectives

<!-- Tại sao cần governance? Risk model + AI ethics + business assurance -->

- Đảm bảo AI decision **explainable + auditable + reversible**
- Prevent **autonomous unsafe action** - mọi action có safety boundary
- **Compliance**: model behavior phù hợp policy + regulation
- **Reproducibility**: same input → same output (deterministic where possible) + audit trail

### 5.2 Scope (Capstone Year-1 equivalent)

- **In-scope**:
  - Single LLM provider (Bedrock) + 1-2 model versions
  - Assist-only decision (human-in-the-loop hoặc safety guardrail)
  - Multi-tenant với per-tenant context isolation
  - Eval methodology + drift detection
- **Out-of-scope** (defer to post-capstone):
  - Multi-provider failover
  - Fine-tuning own model
  - Autonomous action without safety gate
  - Cross-region model serving

### 5.3 Key Governance Principles

| Principle | Rationale | Enforcement |
|---|---|---|
| **Explainability** | Mọi decision có reasoning chain | Output schema includes `reasoning` field |
| **Auditability** | Trace decision input → output | Mandatory audit log với input_hash |
| **Confidence-gated action** | Low-confidence → escalate, không auto-act | Threshold trong code |
| **Reversibility** | Mọi action có rollback path | Dry-run mode + action queue |
| **Tenant isolation** | No cross-tenant context bleed | Per-request scoping + audit assertion |
| **Cost guard** | Spend không vượt quota | Per-tenant token quota + alarm |
| **Drift detection** | Model behavior drift detected sớm | Weekly eval re-run + compare baseline |

### 5.4 Enforcement Mechanisms (Architectural)

| Mechanism | Implementation | Layer |
|---|---|---|
| Input sanitization | Pydantic Schema Validation (reject if invalid schema/type) | API Layer |
| Output schema validation | JSON schema enforce, reject if invalid | Post-Processing |
| Confidence threshold | App-level: confidence < 0.6 → `INVESTIGATE` | App layer |
| Audit log mandatory | Cannot return response without audit entry | App layer |
| Per-tenant isolation | Context isolation via `tenant_id` header | App layer |
| Rate limit | API Gateway usage plan per tenant | Edge |
| Circuit breaker | API threshold 60%+ error → fallback rule-based | App layer |
| Eval baseline check | Scheduled re-run eval set, alert nếu metrics drop | CI/CD job |

### 5.5 Model NFR Control Matrix

| NFR ID | Category | Requirement | Control | Evidence | Owner |
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
| MG-10 | Safety | Threshold tuning / retrain | Statistical baseline recalculation | Drift detection log | Nhóm AI |

### 5.6 Closed-loop Safety Pattern (chỉ áp dụng cho engine có ACTION - Self-Heal type)

<!-- Skip section này nếu engine chỉ ALERT/SUGGEST, không EXECUTE action.
     Self-Heal Engine + auto-containment engines BẮT BUỘC có section này. -->

Pattern bắt buộc cho mọi engine thực hiện action thật trên hệ thống (không phải chỉ suggest):

![Closed-loop Safety Pattern](../diagrams/03_ai_action_loop.png)

*(Sơ đồ có thể chỉnh sửa: [03_ai_action_loop.drawio](../diagrams/03_ai_action_loop.drawio))*

#### 5.6.1 Five sub-checkpoints (mọi action phải qua tất cả 5)

| # | Checkpoint | Spec | Capstone evidence |
|---|---|---|---|
| 1 | **Dry-run mode** | Mọi action có dry-run path; CI/CD test dry-run trước deploy | Test case dry-run + screenshot |
| 2 | **Blast-radius config** | Per-action limit: max % cluster · max N pod · max region · max $ cost impact | YAML config + ADR |
| 3 | **Verify post-act** | Metric check sau action: timeout N sec, threshold M | Verify rule code + test case |
| 4 | **Auto rollback** | Verify fail → automatic rollback to pre-action state; rollback also verified | Rollback code + chaos test |
| 5 | **Circuit breaker** | Consecutive K failures (vd 3) → halt automation, force manual escalation | Circuit breaker state machine + alert |

#### 5.6.2 Configuration example

```yaml
# action_safety_config.yaml
action: restart_pod_oom
dry_run:
  enabled: true
  mandatory_in_ci: true
blast_radius:
  max_pods_per_action: 3
  max_pods_per_namespace_per_hour: 10
  max_clusters_affected: 1
verify:
  enabled: true
  check_metric: container_memory_usage_bytes
  threshold: "< 80% of limit"
  timeout_seconds: 300
  sample_count: 3
rollback:
  enabled: true
  rollback_action: restore_pod_spec_from_snapshot
  rollback_verify: true
circuit_breaker:
  consecutive_failure_threshold: 3
  cool_down_seconds: 1800
  halt_action: page_oncall_critical
audit:
  log_all_steps: true
  retention_days: 90
```

#### 5.6.3 Test coverage requirement

Capstone: ≥3 chaos test scenarios chứng minh verify-fail → rollback hoạt động:
- Test 1: action thành công → verify pass → audit log đầy đủ
- Test 2: action chạy nhưng verify fail → rollback trigger → state restored
- Test 3: 3 consecutive failure → circuit breaker halt → manual escalation triggered

## 6. Statistical Engine Security (Thay thế AI Security)

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
  "model_version": "tf4-ewma-stl-v1",
  "input_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "data_encryption": "AWS KMS CMK",
  "decision": "SCALE_UP",
  "confidence": 1.0,
  "execution_ms": 5.42
}
```

## 7. Eval methodology

- **Test set composition**: synthetic <N> + real-anonymized <M> = total ≥10 scenarios
- **Metrics tracked**:
  - Precision (true positive / predicted positive)
  - Recall (true positive / actual positive)
  - F1
  - P50 / P99 latency
  - Cost per correct decision
- **Acceptance threshold**:
  - Precision ≥ 0.8
  - Recall ≥ 0.7
  - P99 latency < Xms
- **Eval set location**: `<repo>/ai-engine/eval/` (JSON)

## 8. Cost model

| Item | Per call | Per day (forecast) | Per tenant/month |
|---|---|---|---|
| Compute (FastAPI Container) | $0.000001 | $0.10 | $0.50 |
| Storage (Audit logs in S3/DynamoDB) | - | $0.01 | $0.10 |
| **Total** | | | **~$1.00 (Nằm rất an toàn dưới giới hạn $200)** |

## 9. Deployment topology

- **Compute**: <ECS Fargate / Lambda / SageMaker endpoint>
- **Replica strategy**: min 2, max 10, autoscale by CPU/queue
- **Cold start mitigation**: <vd provisioned concurrency>
- **Region**: <region + multi-AZ>
- **Network**: private subnet, internal ALB
- **Secrets**: Secrets Manager (Bedrock IAM, không API key)

## Related documents

- [`02_solution_design.md`](02_solution_design.md) - high-level architecture context
- [`04_eval_report.md`](04_eval_report.md) - eval methodology + results feeding NFR MG-04, MG-08
- [`05_adrs.md`](05_adrs.md) - ADRs for model/governance decisions
- [`../contracts/ai-api-contract.md`](../contracts/ai-api-contract.md) - API exposed to CDO
- [`../../cdo/docs/03_security_design.md`](../../cdo/docs/03_security_design.md) - platform-level security (AI security details ở §6 doc này)
- [`../../cdo/docs/05_cost_analysis.md`](../../cdo/docs/05_cost_analysis.md) - total cost includes AI inference từ §8 doc này
