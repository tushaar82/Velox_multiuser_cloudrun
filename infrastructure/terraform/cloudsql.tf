# Cloud SQL PostgreSQL Configuration

# Primary Cloud SQL Instance
resource "google_sql_database_instance" "primary" {
  name             = "trading-platform-db-${var.environment}"
  database_version = "POSTGRES_15"
  region           = var.region
  
  depends_on = [google_service_networking_connection.private_vpc_connection]
  
  settings {
    tier              = var.db_instance_tier
    availability_type = "REGIONAL"  # High availability
    disk_type         = "PD_SSD"
    disk_size         = 100  # GB
    disk_autoresize   = true
    
    backup_configuration {
      enabled                        = true
      start_time                     = "02:00"  # 2 AM IST
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = var.backup_retention_days
      backup_retention_settings {
        retained_backups = var.backup_retention_days
      }
    }
    
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc.id
      require_ssl     = true
    }
    
    database_flags {
      name  = "max_connections"
      value = "500"
    }
    
    database_flags {
      name  = "shared_buffers"
      value = "4194304"  # 4GB in 8KB pages
    }
    
    database_flags {
      name  = "effective_cache_size"
      value = "12582912"  # 12GB in 8KB pages
    }
    
    database_flags {
      name  = "maintenance_work_mem"
      value = "1048576"  # 1GB in KB
    }
    
    database_flags {
      name  = "checkpoint_completion_target"
      value = "0.9"
    }
    
    database_flags {
      name  = "wal_buffers"
      value = "16384"  # 16MB in 8KB pages
    }
    
    database_flags {
      name  = "default_statistics_target"
      value = "100"
    }
    
    database_flags {
      name  = "random_page_cost"
      value = "1.1"  # SSD optimization
    }
    
    database_flags {
      name  = "effective_io_concurrency"
      value = "200"  # SSD optimization
    }
    
    insights_config {
      query_insights_enabled  = true
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = true
    }
    
    maintenance_window {
      day          = 7  # Sunday
      hour         = 3  # 3 AM IST
      update_track = "stable"
    }
  }
  
  deletion_protection = true
}

# Database
resource "google_sql_database" "database" {
  name     = var.db_name
  instance = google_sql_database_instance.primary.name
}

# Database User
resource "google_sql_user" "user" {
  name     = var.db_user
  instance = google_sql_database_instance.primary.name
  password = random_password.db_password.result
}

# Read Replica for Analytics Queries
resource "google_sql_database_instance" "read_replica" {
  count = var.enable_read_replicas ? 1 : 0
  
  name                 = "trading-platform-db-replica-${var.environment}"
  master_instance_name = google_sql_database_instance.primary.name
  region               = var.region
  database_version     = "POSTGRES_15"
  
  replica_configuration {
    failover_target = false
  }
  
  settings {
    tier              = var.db_instance_tier
    availability_type = "ZONAL"
    disk_type         = "PD_SSD"
    disk_size         = 100
    disk_autoresize   = true
    
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc.id
      require_ssl     = true
    }
    
    database_flags {
      name  = "max_connections"
      value = "500"
    }
    
    insights_config {
      query_insights_enabled  = true
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = true
    }
  }
  
  deletion_protection = false
}

# PgBouncer Configuration (to be deployed as Cloud Run service)
# Connection pooling configuration
locals {
  pgbouncer_config = {
    pool_mode           = "transaction"
    max_client_conn     = 1000
    default_pool_size   = 20
    reserve_pool_size   = 5
    reserve_pool_timeout = 3
    max_db_connections  = 100
    server_idle_timeout = 600
    server_lifetime     = 3600
  }
}
