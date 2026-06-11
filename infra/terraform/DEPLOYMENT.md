# AWS Deployment Guide

## Prerequisites

- AWS CLI configured with admin access to the target account
- Terraform ≥ 1.7 installed
- A registered domain with Route 53 (or external DNS you can update)
- An ACM certificate covering your API and web domains (must be in `us-east-1` for ALB)

---

## Step 1 — Bootstrap Terraform remote state

Run once per AWS account. Creates the S3 bucket and DynamoDB table for state.

```bash
cd infra/terraform/bootstrap
terraform init
terraform apply
```

Note the `state_bucket` output value — replace `ACCOUNT_ID` placeholders in:
- `environments/staging/backend.hcl`
- `environments/production/backend.hcl`

---

## Step 2 — Configure environment-specific values

Edit `environments/staging/terraform.tfvars` and `environments/production/terraform.tfvars`:

1. Replace `api_domain` and `web_domain` with real domains.
2. Replace `acm_certificate_arn` with the ARN from ACM.

---

## Step 3 — First Terraform apply (staging)

```bash
cd infra/terraform
terraform init -backend-config=environments/staging/backend.hcl
terraform apply \
  -var-file=environments/staging/terraform.tfvars \
  -var="api_image_tag=latest" \
  -var="web_image_tag=latest"
```

This creates: VPC, ECR repos, RDS, ElastiCache, Secrets Manager, ECS cluster + services, ALBs.

Note the `api_ecr_url` and `web_ecr_url` outputs — you'll need them in Step 4.

---

## Step 4 — Post-apply: replace generated secrets

The Secrets Manager secret is seeded with random placeholder values for
`CONNECTOR_ENCRYPTION_KEY` (and other secrets). Replace it with a real Fernet key:

```bash
# Generate a real Fernet key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Update the secret (staging example)
aws secretsmanager put-secret-value \
  --secret-id "aic-staging/app-secrets" \
  --secret-string "$(
    aws secretsmanager get-secret-value \
      --secret-id aic-staging/app-secrets \
      --query SecretString --output text \
    | python -c "
import sys, json
s = json.load(sys.stdin)
s['CONNECTOR_ENCRYPTION_KEY'] = 'YOUR_FERNET_KEY_HERE'
print(json.dumps(s))
    "
  )"
```

Redeploy the API and Celery services after updating secrets.

---

## Step 5 — Wire GitHub Actions

Required **GitHub Secrets** (Settings → Secrets and variables → Actions):

| Secret | Value |
|--------|-------|
| `AWS_DEPLOY_ROLE_ARN` | ARN of the IAM role for GitHub OIDC (see below) |
| `API_ECR_REPO` | ECR repo name from Terraform output `api_ecr_url` (just the repo name, not full URL) |
| `WEB_ECR_REPO` | ECR repo name from Terraform output `web_ecr_url` |

Required **GitHub Variables**:

| Variable | Value |
|----------|-------|
| `API_BASE_URL` | e.g. `https://api-staging.example.com` |

### Create the GitHub OIDC IAM role

```bash
# Replace ACCOUNT_ID and YOUR_ORG/YOUR_REPO with real values
aws iam create-role \
  --role-name aic-github-deploy \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": { "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com" },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": { "token.actions.githubusercontent.com:aud": "sts.amazonaws.com" },
        "StringLike":   { "token.actions.githubusercontent.com:sub": "repo:YOUR_ORG/YOUR_REPO:*" }
      }
    }]
  }'

# Attach deploy policy (you'll want to scope this down for production)
aws iam attach-role-policy \
  --role-name aic-github-deploy \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
```

---

## Step 6 — DNS

Point your `api_domain` and `web_domain` DNS CNAME records at the ALB DNS names
from the Terraform outputs `api_alb_dns` and `web_alb_dns`.

---

## Subsequent deploys

Push to `main` → CI runs tests → Docker images built & pushed → Terraform plan/apply
→ ECS rolling deploy.

For production, trigger manually via GitHub Actions → Deploy → Run workflow → choose
`production`.

---

## Rollback

ECS deployment circuit breaker is enabled — failed deploys auto-rollback to the
previous task definition. Manual rollback:

```bash
aws ecs update-service \
  --cluster aic-production-cluster \
  --service aic-production-api \
  --task-definition aic-production-api:<PREVIOUS_REVISION>
```
