# Bootstrap: creates S3 bucket + DynamoDB table for remote Terraform state.
# Run ONCE before applying any other Terraform configuration.
# This module uses local state (committed to the repo is fine since it only
# manages the state bucket itself — no secrets are stored here).

terraform {
  required_version = ">= 1.7"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}

locals {
  bucket_name = "aic-terraform-state-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket" "state" {
  bucket        = local.bucket_name
  force_destroy = false
  tags          = { Name = local.bucket_name, ManagedBy = "terraform-bootstrap" }
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_dynamodb_table" "locks" {
  name         = "aic-terraform-locks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = { Name = "aic-terraform-locks", ManagedBy = "terraform-bootstrap" }
}

output "state_bucket" { value = local.bucket_name }
output "locks_table"  { value = aws_dynamodb_table.locks.name }

variable "aws_region" {
  type    = string
  default = "us-east-1"
}
