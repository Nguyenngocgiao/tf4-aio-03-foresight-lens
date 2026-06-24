# Workspace Rules for XBrain Learner (Capstone Phase)

These are the global instructions for Antigravity (Gemini CLI) when operating in this workspace.

## 1. Project Context
- This repository contains lab exercises and capstone projects for the XBrain AWS DevOps/CloudOps Foundation Program.
- We are currently in **Capstone Phase 2 (W11-W12)**.
- The user belongs to the **AI Group** and must collaborate with the **CDO Group (Cloud/DevOps)** via strict API contracts.

## 2. Architecture & Backend Services
- **Starter Apps (BudgetBot, DocHub, StudyBot):** These are FastAPI applications using Pydantic, Boto3, and Pytest.
- **Local vs AWS Backends:** By default, for local development, always use the `local` fallbacks (`AI_BACKEND=local`, `STORAGE_BACKEND=local`, `VECTOR_BACKEND=local`, `USERSTORE_BACKEND=sqlite`) to avoid requiring AWS credentials.
- Do not modify `.env` to use `bedrock`, `s3`, or `dynamodb` unless explicitly requested to test AWS integration.

## 3. Workflow for W11-W12
- **Contracts First:** Any new feature or module must have its interface documented in a Contract (Telemetry, AI API, Deployment) before implementation.
- **Engine Skeleton:** Ensure a dummy/skeleton endpoint is deployable for the CDO group to integrate against. It must strictly follow the defined request/response JSON schemas.
- Do not jump into deep AI model implementation (e.g., complex RAG logic) without first solidifying the API schema and contracts.

## 4. Coding Standards & Testing
- Enforce strict typing with Python type hints.
- Validate inputs using `pydantic` models.
- Any new endpoint must be covered by a `pytest` test case. 
- Run tests via `pytest` to verify endpoints.

## 5. Evidence & Jira Tracking
- All documents (Spec, Contracts, ADRs) must be committed to the repo, as git history is the primary evidence for grading.
- Update Jira task status and link git commits as evidence for each task.

## 6. Git & Team Collaboration Rules
- **No Selfish Commits:** NEVER commit directly to the `master` or `main` branch. Always checkout a new feature branch (e.g. `feature/...`) before writing code.
- **Co-authored Commits:** Every commit message MUST include `Co-authored-by:` footers to credit all team members. Use this list:
  Co-authored-by: Nguyen Cong Thinh <nguyencongthinh.dev@gmail.com>
  Co-authored-by: Tai <taitotang233@gmail.com>
  Co-authored-by: Dung <lkdung0612@gmail.com>
  Co-authored-by: Vinh <vinh2901200@gmail.com>
  Co-authored-by: Thinh <nghungthinh05@gmail.com>
  Co-authored-by: Thanh <phamthanh.forwork@gmail.com>
  Co-authored-by: Giao <nguyenngocgiao0912pct@gmail.com>
  Co-authored-by: Our Life <ourlife937@gmail.com>
