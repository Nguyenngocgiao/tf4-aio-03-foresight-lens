# Deployment Contract - Task force 4

<!-- Owner: AIO-03
     Signed by: AI Lead + CDO Leads × 2-3 + Reviewer panel
     Date signed: 2026-06-25 (W11 T5)
     🔒 FREEZE - no change without formal change request -->

## Mục đích

Định nghĩa **AI Engine deploy như thế nào** - compute target, scale, secrets, network, rollback. CDO platform cần thông tin này để config infra connect.

## Key principle

**Nhóm AI host AI engine ONCE per task force.** Các CDO infra trong task force cùng trỏ tới endpoint, multi-tenant theo `X-Tenant-Id`.

---

## Compute

| Aspect | Configuration |
|---|---|
| **Target** | ECS Fargate task (Stateless FastAPI) |
| **Cluster** | `tf-4-aiops-cluster` |
| **Service name** | `foresight-lens-engine` |
| **Image source** | ECR repo URI + image tag |
| **CPU per task** | 1024 (1 vCPU) |
| **Memory per task** | 2048 MB |

## Scaling

| Aspect | Value |
|---|---|
| **Replicas** | min 2, max 10 |
| **Autoscale trigger 1** | Target CPU 70% |
| **Autoscale trigger 2** | Target request count 1000 per task |
| **Scale-up cooldown** | 60 giây |

## Secrets

> Hệ thống sử dụng thuật toán Statistical 3-Sigma, KHÔNG dùng Bedrock LLM. Do đó, KHÔNG yêu cầu API Key của Bedrock.

| Secret name | Source |
|---|---|
| `AWS_REGION` | env var |

## Networking

| Aspect | Configuration |
|---|---|
| **Subnet type** | private |
| **ALB** | internal only (không public-facing) |
| **Security group** | `tf-4-ai-engine-sg` |
| **Ingress rules** | chỉ allow từ CDO platforms trong cùng task force (SG-to-SG reference) |
| **Egress rules** | Không cần egress external (Engine chạy thuần toán học local) |
| **DNS** | resolve được trong VPC (route 53 private hosted zone) |

## Deployment topology diagram

```mermaid
graph TB
    subgraph "VPC Task Force 4"
        subgraph "Private subnet"
            ALB[Internal ALB]
            ECS[ECS Fargate Tasks × min 2]
            ALB -->|Forward to FastAPI| ECS
        end
    end

    subgraph "CDO Platforms"
        CDO1[CDO-Payment]
        CDO2[CDO-Fraud]
        CDO3[CDO-Ledger]
    end
    CDO1 -->|POST /v1/detect| ALB
    CDO2 -->|POST /v1/detect| ALB
    CDO3 -->|POST /v1/detect| ALB
```

## Per-CDO platform pointer

| CDO platform | Endpoint URL | Auth |
|---|---|---|
| CDO-Payment | `https://ai-engine.tf-4.internal/` | IAM SigV4 |
| CDO-Fraud | (same - shared) | IAM SigV4 |
| CDO-Ledger | (same - shared) | IAM SigV4 |

## Failure modes & response

| Failure | Detection | Response |
|---|---|---|
| Task crash | ECS health check | Auto-restart |
| Region outage | CloudWatch alarm | Failover secondary region |
| Throttling | ALB 5xx / 429 | CDO fallback về Rule-based Alert |
| Memory leak | Memory > 90% | Rolling restart ECS task |
