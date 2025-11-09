# Google Secret Manager Configuration

# Enable Secret Manager API
resource "google_project_service" "secretmanager" {
  service = "secretmanager.googleapis.com"
  disable_on_destroy = false
}

# Database URL Secret
resource "google_secret_manager_secret" "database_url" {
  secret_id = "database-url"
  
  replication {
    automatic = true
  }
  
  labels = {
    environment = var.environment
    service     = "trading-platform"
    component   = "database"
  }
  
  rotation {
    next_rotation_time = timeadd(timestamp(), "2160h")  # 90 days
    rotation_period    = "7776000s"  # 90 days in seconds
  }
  
  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret_version" "database_url" {
  secret = google_secret_manager_secret.database_url.id
  
  secret_data = "postgresql://${google_sql_user.user.name}:${random_password.db_password.result}@${google_sql_database_instance.primary.private_ip_address}:5432/${google_sql_database.database.name}"
}

# Database Replica URL Secret (for analytics)
resource "google_secret_manager_secret" "database_replica_url" {
  count     = var.enable_read_replicas ? 1 : 0
  secret_id = "database-replica-url"
  
  replication {
    automatic = true
  }
  
  labels = {
    environment = var.environment
    service     = "trading-platform"
    component   = "database"
  }
  
  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret_version" "database_replica_url" {
  count  = var.enable_read_replicas ? 1 : 0
  secret = google_secret_manager_secret.database_replica_url[0].id
  
  secret_data = "postgresql://${google_sql_user.user.name}:${random_password.db_password.result}@${google_sql_database_instance.read_replica[0].private_ip_address}:5432/${google_sql_database.database.name}"
}

# Redis Host Secret
resource "google_secret_manager_secret" "redis_host" {
  secret_id = "redis-host"
  
  replication {
    automatic = true
  }
  
  labels = {
    environment = var.environment
    service     = "trading-platform"
    component   = "cache"
  }
  
  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret_version" "redis_host" {
  secret = google_secret_manager_secret.redis_host.id
  
  secret_data = google_redis_instance.cache.host
}

# JWT Secret Key
resource "random_password" "jwt_secret" {
  length  = 64
  special = true
}

resource "google_secret_manager_secret" "jwt_secret_key" {
  secret_id = "jwt-secret-key"
  
  replication {
    automatic = true
  }
  
  labels = {
    environment = var.environment
    service     = "trading-platform"
    component   = "auth"
  }
  
  rotation {
    next_rotation_time = timeadd(timestamp(), "2160h")  # 90 days
    rotation_period    = "7776000s"  # 90 days in seconds
  }
  
  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret_version" "jwt_secret_key" {
  secret = google_secret_manager_secret.jwt_secret_key.id
  
  secret_data = random_password.jwt_secret.result
}

# InfluxDB URL Secret
resource "google_secret_manager_secret" "influxdb_url" {
  secret_id = "influxdb-url"
  
  replication {
    automatic = true
  }
  
  labels = {
    environment = var.environment
    service     = "trading-platform"
    component   = "timeseries"
  }
  
  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret_version" "influxdb_url" {
  secret = google_secret_manager_secret.influxdb_url.id
  
  secret_data = var.influxdb_url
}

# InfluxDB Token Secret
resource "google_secret_manager_secret" "influxdb_token" {
  secret_id = "influxdb-token"
  
  replication {
    automatic = true
  }
  
  labels = {
    environment = var.environment
    service     = "trading-platform"
    component   = "timeseries"
  }
  
  rotation {
    next_rotation_time = timeadd(timestamp(), "2160h")  # 90 days
    rotation_period    = "7776000s"  # 90 days in seconds
  }
  
  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret_version" "influxdb_token" {
  secret = google_secret_manager_secret.influxdb_token.id
  
  secret_data = var.influxdb_token
}

# Angel One API Key Secret (placeholder - to be updated manually)
resource "google_secret_manager_secret" "angel_one_api_key" {
  secret_id = "angel-one-api-key"
  
  replication {
    automatic = true
  }
  
  labels = {
    environment = var.environment
    service     = "trading-platform"
    component   = "broker"
  }
  
  rotation {
    next_rotation_time = timeadd(timestamp(), "2160h")  # 90 days
    rotation_period    = "7776000s"  # 90 days in seconds
  }
  
  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret_version" "angel_one_api_key" {
  secret = google_secret_manager_secret.angel_one_api_key.id
  
  secret_data = "PLACEHOLDER_UPDATE_MANUALLY"
}

# IAM bindings for service account to access secrets
resource "google_secret_manager_secret_iam_member" "database_url_access" {
  secret_id = google_secret_manager_secret.database_url.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:trading-platform-sa@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_secret_manager_secret_iam_member" "redis_host_access" {
  secret_id = google_secret_manager_secret.redis_host.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:trading-platform-sa@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_secret_manager_secret_iam_member" "jwt_secret_access" {
  secret_id = google_secret_manager_secret.jwt_secret_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:trading-platform-sa@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_secret_manager_secret_iam_member" "influxdb_url_access" {
  secret_id = google_secret_manager_secret.influxdb_url.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:trading-platform-sa@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_secret_manager_secret_iam_member" "influxdb_token_access" {
  secret_id = google_secret_manager_secret.influxdb_token.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:trading-platform-sa@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_secret_manager_secret_iam_member" "angel_one_api_key_access" {
  secret_id = google_secret_manager_secret.angel_one_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:trading-platform-sa@${var.project_id}.iam.gserviceaccount.com"
}

# Outputs
output "secrets_created" {
  value = {
    database_url       = google_secret_manager_secret.database_url.name
    redis_host         = google_secret_manager_secret.redis_host.name
    jwt_secret_key     = google_secret_manager_secret.jwt_secret_key.name
    influxdb_url       = google_secret_manager_secret.influxdb_url.name
    influxdb_token     = google_secret_manager_secret.influxdb_token.name
    angel_one_api_key  = google_secret_manager_secret.angel_one_api_key.name
  }
  description = "List of created secrets"
}
