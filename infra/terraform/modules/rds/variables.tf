variable "prefix"                  { type = string }
variable "vpc_id"                  { type = string }
variable "subnet_ids"              { type = list(string) }
variable "allowed_security_groups" { type = list(string) }
variable "db_name"                 { type = string }
variable "db_username"             { type = string; sensitive = true }
variable "instance_class"          { type = string }
variable "allocated_storage_gb"    { type = number }
variable "backup_retention_days"   { type = number }
variable "environment"             { type = string }
