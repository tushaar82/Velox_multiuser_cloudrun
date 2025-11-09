# Cloud Memorystore Redis Configuration

# Redis Instance
resource "google_redis_instance" "cache" {
  name               = "trading-platform-redis-${var.environment}"
  tier               = var.redis_tier
  memory_size_gb     = var.redis_memory_size_gb
  region             = var.region
  redis_version      = "REDIS_7_0"
  display_name       = "Trading Platform Redis Cache"
  reserved_ip_range  = "10.1.0.0/29"
  
  authorized_network = google_compute_network.vpc.id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"
  
  redis_configs = {
    maxmemory-policy           = "allkeys-lru"
    notify-keyspace-events     = "Ex"  # Enable keyspace notifications for expiration
    timeout                    = "300"
    tcp-keepalive              = "60"
    maxmemory-gb               = tostring(var.redis_memory_size_gb * 0.9)  # 90% of total
  }
  
  maintenance_policy {
    weekly_maintenance_window {
      day = "SUNDAY"
      start_time {
        hours   = 3
        minutes = 0
      }
    }
  }
  
  persistence_config {
    persistence_mode    = "RDB"
    rdb_snapshot_period = "TWELVE_HOURS"
  }
  
  # High availability configuration (only for STANDARD_HA tier)
  replica_count = var.redis_tier == "STANDARD_HA" ? 1 : 0
  read_replicas_mode = var.redis_tier == "STANDARD_HA" ? "READ_REPLICAS_ENABLED" : "READ_REPLICAS_DISABLED"
  
  labels = {
    environment = var.environment
    service     = "trading-platform"
    component   = "cache"
  }
}

# Output Redis connection details
output "redis_host" {
  value       = google_redis_instance.cache.host
  description = "Redis instance host"
}

output "redis_port" {
  value       = google_redis_instance.cache.port
  description = "Redis instance port"
}

output "redis_connection_string" {
  value       = "redis://${google_redis_instance.cache.host}:${google_redis_instance.cache.port}"
  description = "Redis connection string"
  sensitive   = true
}
