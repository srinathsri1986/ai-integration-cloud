# S3 backend config for production
# Apply with: terraform init -backend-config=environments/production/backend.hcl
bucket         = "aic-terraform-state-ACCOUNT_ID"
region         = "us-east-1"
dynamodb_table = "aic-terraform-locks"
key            = "ai-integration-cloud/production/terraform.tfstate"
