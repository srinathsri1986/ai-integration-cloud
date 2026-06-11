# S3 backend config for staging
# Apply with: terraform init -backend-config=environments/staging/backend.hcl
bucket         = "aic-terraform-state-ACCOUNT_ID"
region         = "us-east-1"
dynamodb_table = "aic-terraform-locks"
key            = "ai-integration-cloud/staging/terraform.tfstate"
