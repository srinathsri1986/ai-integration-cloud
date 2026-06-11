terraform {
  required_version = ">= 1.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Remote state — bucket and table are created by `terraform/bootstrap/` before
  # this root config is first applied.
  backend "s3" {
    # Values provided via -backend-config or environments/<env>/backend.hcl
    key            = "ai-integration-cloud/terraform.tfstate"
    encrypt        = true
    use_lockfile   = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "ai-integration-cloud"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
