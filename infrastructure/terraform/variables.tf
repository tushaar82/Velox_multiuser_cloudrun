# Terraform Variables for GCP Infrastructure

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "asia-south1"  # Mumbai region for NSE trading
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "db_instance_tier" {
  description = "Cloud SQL instance tier"
  type        = string
  default     = "db-custom-4-16384"  # 4 vCPU, 16GB RAM
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "trading_platform"
}

variable "db_user" {
  description = "Database user"
  type        = string
  default     = "trading_user"
}

variable "redis_memory_size_gb" {
  description = "Redis memory size in GB"
  type        = number
  default     = 5
}

variable "redis_tier" {
  description = "Redis service tier (BASIC or STANDARD_HA)"
  type        = string
  default     = "STANDARD_HA"
}

variable "enable_read_replicas" {
  description = "Enable Cloud SQL read replicas"
  type        = bool
  default     = true
}

variable "backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 7
}

variable "influxdb_url" {
  description = "InfluxDB connection URL"
  type        = string
  default     = "http://influxdb:8086"
}

variable "influxdb_token" {
  description = "InfluxDB authentication token"
  type        = string
  sensitive   = true
}

variable "domain_name" {
  description = "Domain name for the load balancer"
  type        = string
  default     = "trading.example.com"
}

variable "alert_email" {
  description = "Email address for monitoring alerts"
  type        = string
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for alerts (optional)"
  type        = string
  default     = ""
  sensitive   = true
}
