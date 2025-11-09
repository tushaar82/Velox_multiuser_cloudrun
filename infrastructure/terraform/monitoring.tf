# Cloud Monitoring and Logging Configuration

# Notification Channel for Alerts
resource "google_monitoring_notification_channel" "email" {
  display_name = "Trading Platform Email Alerts"
  type         = "email"
  
  labels = {
    email_address = var.alert_email
  }
}

resource "google_monitoring_notification_channel" "slack" {
  count        = var.slack_webhook_url != "" ? 1 : 0
  display_name = "Trading Platform Slack Alerts"
  type         = "slack"
  
  labels = {
    url = var.slack_webhook_url
  }
}

# Alert Policy: High Error Rate
resource "google_monitoring_alert_policy" "high_error_rate" {
  display_name = "High Error Rate"
  combiner     = "OR"
  
  conditions {
    display_name = "Error rate > 5%"
    
    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_count\" AND metric.labels.response_code_class=\"5xx\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.05
      
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }
  
  notification_channels = concat(
    [google_monitoring_notification_channel.email.id],
    var.slack_webhook_url != "" ? [google_monitoring_notification_channel.slack[0].id] : []
  )
  
  alert_strategy {
    auto_close = "1800s"
  }
}

# Alert Policy: High Latency
resource "google_monitoring_alert_policy" "high_latency" {
  display_name = "High API Latency"
  combiner     = "OR"
  
  conditions {
    display_name = "95th percentile latency > 2 seconds"
    
    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_latencies\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 2000  # milliseconds
      
      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_DELTA"
        cross_series_reducer = "REDUCE_PERCENTILE_95"
        group_by_fields      = ["resource.service_name"]
      }
    }
  }
  
  notification_channels = concat(
    [google_monitoring_notification_channel.email.id],
    var.slack_webhook_url != "" ? [google_monitoring_notification_channel.slack[0].id] : []
  )
  
  alert_strategy {
    auto_close = "1800s"
  }
}

# Alert Policy: High CPU Usage
resource "google_monitoring_alert_policy" "high_cpu" {
  display_name = "High CPU Usage"
  combiner     = "OR"
  
  conditions {
    display_name = "CPU utilization > 80% for 5 minutes"
    
    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/container/cpu/utilizations\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.8
      
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }
  
  notification_channels = concat(
    [google_monitoring_notification_channel.email.id],
    var.slack_webhook_url != "" ? [google_monitoring_notification_channel.slack[0].id] : []
  )
  
  alert_strategy {
    auto_close = "1800s"
  }
}

# Alert Policy: High Memory Usage
resource "google_monitoring_alert_policy" "high_memory" {
  display_name = "High Memory Usage"
  combiner     = "OR"
  
  conditions {
    display_name = "Memory utilization > 90%"
    
    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/container/memory/utilizations\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.9
      
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }
  
  notification_channels = concat(
    [google_monitoring_notification_channel.email.id],
    var.slack_webhook_url != "" ? [google_monitoring_notification_channel.slack[0].id] : []
  )
  
  alert_strategy {
    auto_close = "1800s"
  }
}

# Alert Policy: Database Connection Failures
resource "google_monitoring_alert_policy" "db_connection_failures" {
  display_name = "Database Connection Failures"
  combiner     = "OR"
  
  conditions {
    display_name = "Failed database connections"
    
    condition_threshold {
      filter          = "resource.type=\"cloudsql_database\" AND metric.type=\"cloudsql.googleapis.com/database/network/connections\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 450  # 90% of max_connections (500)
      
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }
  
  notification_channels = concat(
    [google_monitoring_notification_channel.email.id],
    var.slack_webhook_url != "" ? [google_monitoring_notification_channel.slack[0].id] : []
  )
  
  alert_strategy {
    auto_close = "1800s"
  }
}

# Alert Policy: Redis Memory Usage
resource "google_monitoring_alert_policy" "redis_memory" {
  display_name = "Redis High Memory Usage"
  combiner     = "OR"
  
  conditions {
    display_name = "Redis memory usage > 90%"
    
    condition_threshold {
      filter          = "resource.type=\"redis_instance\" AND metric.type=\"redis.googleapis.com/stats/memory/usage_ratio\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.9
      
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }
  
  notification_channels = concat(
    [google_monitoring_notification_channel.email.id],
    var.slack_webhook_url != "" ? [google_monitoring_notification_channel.slack[0].id] : []
  )
  
  alert_strategy {
    auto_close = "1800s"
  }
}

# Custom Metrics for Trading Activity
resource "google_logging_metric" "orders_per_second" {
  name   = "trading/orders_per_second"
  filter = "resource.type=\"cloud_run_revision\" AND jsonPayload.event=\"order_submitted\""
  
  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    unit        = "1"
    
    labels {
      key         = "trading_mode"
      value_type  = "STRING"
      description = "Trading mode (paper or live)"
    }
  }
  
  label_extractors = {
    "trading_mode" = "EXTRACT(jsonPayload.trading_mode)"
  }
}

resource "google_logging_metric" "strategy_errors" {
  name   = "trading/strategy_errors"
  filter = "resource.type=\"cloud_run_revision\" AND jsonPayload.event=\"strategy_error\""
  
  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    unit        = "1"
    
    labels {
      key         = "strategy_id"
      value_type  = "STRING"
      description = "Strategy ID"
    }
  }
  
  label_extractors = {
    "strategy_id" = "EXTRACT(jsonPayload.strategy_id)"
  }
}

# Log Sink for Long-term Storage
resource "google_logging_project_sink" "storage_sink" {
  name        = "trading-platform-logs-sink"
  destination = "storage.googleapis.com/${google_storage_bucket.logs.name}"
  
  filter = "resource.type=\"cloud_run_revision\" OR resource.type=\"cloudsql_database\" OR resource.type=\"redis_instance\""
  
  unique_writer_identity = true
}

# Storage bucket for logs
resource "google_storage_bucket" "logs" {
  name          = "${var.project_id}-trading-logs"
  location      = var.region
  force_destroy = false
  
  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }
  
  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }
}

# Grant log writer permission to sink
resource "google_storage_bucket_iam_member" "log_writer" {
  bucket = google_storage_bucket.logs.name
  role   = "roles/storage.objectCreator"
  member = google_logging_project_sink.storage_sink.writer_identity
}

# Monitoring Dashboard
resource "google_monitoring_dashboard" "main" {
  dashboard_json = jsonencode({
    displayName = "Trading Platform Dashboard"
    
    gridLayout = {
      widgets = [
        {
          title = "Request Rate"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_count\""
                  aggregation = {
                    alignmentPeriod  = "60s"
                    perSeriesAligner = "ALIGN_RATE"
                  }
                }
              }
            }]
          }
        },
        {
          title = "Error Rate"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_count\" AND metric.labels.response_code_class=\"5xx\""
                  aggregation = {
                    alignmentPeriod  = "60s"
                    perSeriesAligner = "ALIGN_RATE"
                  }
                }
              }
            }]
          }
        },
        {
          title = "Latency (95th percentile)"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_latencies\""
                  aggregation = {
                    alignmentPeriod    = "60s"
                    perSeriesAligner   = "ALIGN_DELTA"
                    crossSeriesReducer = "REDUCE_PERCENTILE_95"
                  }
                }
              }
            }]
          }
        },
        {
          title = "CPU Utilization"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/container/cpu/utilizations\""
                  aggregation = {
                    alignmentPeriod  = "60s"
                    perSeriesAligner = "ALIGN_MEAN"
                  }
                }
              }
            }]
          }
        },
        {
          title = "Memory Utilization"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/container/memory/utilizations\""
                  aggregation = {
                    alignmentPeriod  = "60s"
                    perSeriesAligner = "ALIGN_MEAN"
                  }
                }
              }
            }]
          }
        },
        {
          title = "Database Connections"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type=\"cloudsql_database\" AND metric.type=\"cloudsql.googleapis.com/database/network/connections\""
                  aggregation = {
                    alignmentPeriod  = "60s"
                    perSeriesAligner = "ALIGN_MEAN"
                  }
                }
              }
            }]
          }
        },
        {
          title = "Redis Memory Usage"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "resource.type=\"redis_instance\" AND metric.type=\"redis.googleapis.com/stats/memory/usage_ratio\""
                  aggregation = {
                    alignmentPeriod  = "60s"
                    perSeriesAligner = "ALIGN_MEAN"
                  }
                }
              }
            }]
          }
        },
        {
          title = "Orders Per Second"
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"logging.googleapis.com/user/trading/orders_per_second\""
                  aggregation = {
                    alignmentPeriod  = "60s"
                    perSeriesAligner = "ALIGN_RATE"
                  }
                }
              }
            }]
          }
        }
      ]
    }
  })
}

# Outputs
output "monitoring_dashboard_url" {
  value       = "https://console.cloud.google.com/monitoring/dashboards/custom/${google_monitoring_dashboard.main.id}?project=${var.project_id}"
  description = "URL to monitoring dashboard"
}

output "logs_bucket" {
  value       = google_storage_bucket.logs.name
  description = "Logs storage bucket name"
}
