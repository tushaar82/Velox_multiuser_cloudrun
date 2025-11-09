# Terraform Outputs

# Cloud SQL Outputs
output "cloudsql_instance_name" {
  value       = google_sql_database_instance.primary.name
  description = "Cloud SQL instance name"
}

output "cloudsql_connection_name" {
  value       = google_sql_database_instance.primary.connection_name
  description = "Cloud SQL connection name for Cloud Run"
}

output "cloudsql_private_ip" {
  value       = google_sql_database_instance.primary.private_ip_address
  description = "Cloud SQL private IP address"
}

output "database_name" {
  value       = google_sql_database.database.name
  description = "Database name"
}

output "database_user" {
  value       = google_sql_user.user.name
  description = "Database user"
}

output "database_password" {
  value       = random_password.db_password.result
  description = "Database password"
  sensitive   = true
}

output "database_url" {
  value       = "postgresql://${google_sql_user.user.name}:${random_password.db_password.result}@${google_sql_database_instance.primary.private_ip_address}:5432/${google_sql_database.database.name}"
  description = "Database connection URL"
  sensitive   = true
}

# Read Replica Outputs
output "read_replica_connection_name" {
  value       = var.enable_read_replicas ? google_sql_database_instance.read_replica[0].connection_name : null
  description = "Read replica connection name"
}

output "read_replica_private_ip" {
  value       = var.enable_read_replicas ? google_sql_database_instance.read_replica[0].private_ip_address : null
  description = "Read replica private IP address"
}

# Network Outputs
output "vpc_network_name" {
  value       = google_compute_network.vpc.name
  description = "VPC network name"
}

output "subnet_name" {
  value       = google_compute_subnetwork.subnet.name
  description = "Subnet name"
}

# PgBouncer Configuration
output "pgbouncer_config" {
  value       = local.pgbouncer_config
  description = "PgBouncer configuration parameters"
}
