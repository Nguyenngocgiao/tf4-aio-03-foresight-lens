# Foresight Lens — Fargate deploy runbook

Hosts the AI engine ONCE per task force on ECS Fargate behind an internal ALB, per
`contracts/deployment-contract.md`. The 3 CDO platforms point at the same endpoint and
are isolated by `X-Tenant-Id`.

## Config (must match deployment-contract.md)
| Item | Value |
|---|---|
| Cluster | `tf-4-aiops-cluster` |
| Service | `foresight-lens-engine` |
| Task | 0.5 vCPU / 1024 MB, min 2 / max 4 |
| Port / health | `8080` / `GET /health` |
| Network | private subnet, internal ALB only, SG `tf-4-ai-engine-sg` |
| Baseline | S3 `tf4-foresight-baselines/baselines/<service>.json` |

## 0. One-time: train + upload baselines
```bash
pip install -r requirements-train.txt
python scripts/train_baseline.py                       # writes engine-skeleton/baselines/*.json
aws s3 sync engine-skeleton/baselines s3://tf4-foresight-baselines/baselines/
```

## 1. Build & push image to ECR
```bash
AWS_REGION=ap-southeast-1
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR=$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/foresight-lens-engine

aws ecr create-repository --repository-name foresight-lens-engine 2>/dev/null || true
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR
docker build -t $ECR:latest engine-skeleton/
docker push $ECR:latest
```

## 2. Register task definition
Fill `<ACCOUNT_ID>` in `task-definition.json`, then:
```bash
aws ecs register-task-definition --cli-input-json file://engine-skeleton/deploy/task-definition.json
```

## 3. Create/update the service (canary per contract: 10%→50%→100%)
```bash
aws ecs create-service \
  --cluster tf-4-aiops-cluster \
  --service-name foresight-lens-engine \
  --task-definition foresight-lens-engine \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[<PRIV_SUBNET_A>,<PRIV_SUBNET_B>],securityGroups=[<SG_ID>],assignPublicIp=DISABLED}" \
  --load-balancers "targetGroupArn=<TG_ARN>,containerName=foresight-lens,containerPort=8080"
```
Autoscaling target CPU 70% / 80 RPS-per-task and ArgoCD/ECS rollback are configured per
the deployment contract (`Scaling`, `Rollback` sections).

## 4. Smoke test (mock data, schema check)
```bash
curl -s -X POST http://ai-engine.tf-4.internal/v1/predict \
  -H "X-Tenant-Id: tnt-alpha" -H "Authorization: SigV4" \
  -H "Content-Type: application/json" \
  -d @engine-skeleton/deploy/sample_request.json | jq .
```

## Cost note
2 tasks × (0.5 vCPU + 1 GB) running 24/7 ≈ **$36–45/month** (flat, request-independent);
$0 inference token cost. Well within the $200 client budget. See `docs/05_cost_analysis.md`.
```
