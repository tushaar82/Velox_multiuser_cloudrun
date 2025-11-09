# Cloud Load Balancer Configuration

# Reserve static IP address
resource "google_compute_global_address" "lb_ip" {
  name = "trading-platform-lb-ip"
}

# SSL Certificate (managed)
resource "google_compute_managed_ssl_certificate" "lb_cert" {
  name = "trading-platform-ssl-cert"
  
  managed {
    domains = [var.domain_name]
  }
}

# Backend service for API Gateway
resource "google_compute_backend_service" "api_gateway" {
  name                  = "api-gateway-backend"
  protocol              = "HTTP"
  port_name             = "http"
  timeout_sec           = 300
  enable_cdn            = false
  load_balancing_scheme = "EXTERNAL_MANAGED"
  
  backend {
    group = google_compute_region_network_endpoint_group.api_gateway_neg.id
    
    balancing_mode  = "UTILIZATION"
    capacity_scaler = 1.0
    max_utilization = 0.8
  }
  
  health_check = google_compute_health_check.api_gateway.id
  
  log_config {
    enable      = true
    sample_rate = 1.0
  }
  
  iap {
    enabled = false
  }
}

# Backend service for WebSocket
resource "google_compute_backend_service" "websocket" {
  name                  = "websocket-backend"
  protocol              = "HTTP"
  port_name             = "http"
  timeout_sec           = 3600  # 1 hour for WebSocket connections
  enable_cdn            = false
  load_balancing_scheme = "EXTERNAL_MANAGED"
  
  backend {
    group = google_compute_region_network_endpoint_group.websocket_neg.id
    
    balancing_mode  = "UTILIZATION"
    capacity_scaler = 1.0
    max_utilization = 0.8
  }
  
  health_check = google_compute_health_check.websocket.id
  
  log_config {
    enable      = true
    sample_rate = 1.0
  }
  
  # Session affinity for WebSocket connections
  session_affinity = "CLIENT_IP"
  affinity_cookie_ttl_sec = 3600
  
  iap {
    enabled = false
  }
}

# Backend service for Analytics
resource "google_compute_backend_service" "analytics" {
  name                  = "analytics-backend"
  protocol              = "HTTP"
  port_name             = "http"
  timeout_sec           = 600
  enable_cdn            = false
  load_balancing_scheme = "EXTERNAL_MANAGED"
  
  backend {
    group = google_compute_region_network_endpoint_group.analytics_neg.id
    
    balancing_mode  = "UTILIZATION"
    capacity_scaler = 1.0
    max_utilization = 0.8
  }
  
  health_check = google_compute_health_check.analytics.id
  
  log_config {
    enable      = true
    sample_rate = 1.0
  }
  
  iap {
    enabled = false
  }
}

# Network Endpoint Groups (NEGs) for Cloud Run services
resource "google_compute_region_network_endpoint_group" "api_gateway_neg" {
  name                  = "api-gateway-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  
  cloud_run {
    service = "api-gateway"
  }
}

resource "google_compute_region_network_endpoint_group" "websocket_neg" {
  name                  = "websocket-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  
  cloud_run {
    service = "websocket-service"
  }
}

resource "google_compute_region_network_endpoint_group" "analytics_neg" {
  name                  = "analytics-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  
  cloud_run {
    service = "analytics-service"
  }
}

# Health checks
resource "google_compute_health_check" "api_gateway" {
  name                = "api-gateway-health-check"
  check_interval_sec  = 10
  timeout_sec         = 5
  healthy_threshold   = 2
  unhealthy_threshold = 3
  
  http_health_check {
    port         = 8080
    request_path = "/health"
  }
}

resource "google_compute_health_check" "websocket" {
  name                = "websocket-health-check"
  check_interval_sec  = 10
  timeout_sec         = 5
  healthy_threshold   = 2
  unhealthy_threshold = 3
  
  http_health_check {
    port         = 8081
    request_path = "/health"
  }
}

resource "google_compute_health_check" "analytics" {
  name                = "analytics-health-check"
  check_interval_sec  = 10
  timeout_sec         = 5
  healthy_threshold   = 2
  unhealthy_threshold = 3
  
  http_health_check {
    port         = 8082
    request_path = "/health"
  }
}

# URL Map
resource "google_compute_url_map" "lb" {
  name            = "trading-platform-lb"
  default_service = google_compute_backend_service.api_gateway.id
  
  host_rule {
    hosts        = [var.domain_name]
    path_matcher = "allpaths"
  }
  
  path_matcher {
    name            = "allpaths"
    default_service = google_compute_backend_service.api_gateway.id
    
    path_rule {
      paths   = ["/ws/*", "/socket.io/*"]
      service = google_compute_backend_service.websocket.id
    }
    
    path_rule {
      paths   = ["/api/analytics/*"]
      service = google_compute_backend_service.analytics.id
    }
    
    path_rule {
      paths   = ["/api/*"]
      service = google_compute_backend_service.api_gateway.id
    }
  }
}

# HTTPS Proxy
resource "google_compute_target_https_proxy" "lb" {
  name             = "trading-platform-https-proxy"
  url_map          = google_compute_url_map.lb.id
  ssl_certificates = [google_compute_managed_ssl_certificate.lb_cert.id]
}

# HTTP to HTTPS redirect
resource "google_compute_url_map" "http_redirect" {
  name = "trading-platform-http-redirect"
  
  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

resource "google_compute_target_http_proxy" "http_redirect" {
  name    = "trading-platform-http-proxy"
  url_map = google_compute_url_map.http_redirect.id
}

# Forwarding rules
resource "google_compute_global_forwarding_rule" "https" {
  name                  = "trading-platform-https-rule"
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  port_range            = "443"
  target                = google_compute_target_https_proxy.lb.id
  ip_address            = google_compute_global_address.lb_ip.id
}

resource "google_compute_global_forwarding_rule" "http" {
  name                  = "trading-platform-http-rule"
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  port_range            = "80"
  target                = google_compute_target_http_proxy.http_redirect.id
  ip_address            = google_compute_global_address.lb_ip.id
}

# Cloud Armor security policy
resource "google_compute_security_policy" "lb_policy" {
  name = "trading-platform-security-policy"
  
  # Rate limiting rule
  rule {
    action   = "rate_based_ban"
    priority = 1000
    
    match {
      versioned_expr = "SRC_IPS_V1"
      
      config {
        src_ip_ranges = ["*"]
      }
    }
    
    rate_limit_options {
      conform_action = "allow"
      exceed_action  = "deny(429)"
      
      enforce_on_key = "IP"
      
      rate_limit_threshold {
        count        = 1000
        interval_sec = 60
      }
      
      ban_duration_sec = 600
    }
    
    description = "Rate limit: 1000 requests per minute per IP"
  }
  
  # Block common attack patterns
  rule {
    action   = "deny(403)"
    priority = 2000
    
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('sqli-stable')"
      }
    }
    
    description = "Block SQL injection attempts"
  }
  
  rule {
    action   = "deny(403)"
    priority = 2001
    
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('xss-stable')"
      }
    }
    
    description = "Block XSS attempts"
  }
  
  # Default rule
  rule {
    action   = "allow"
    priority = 2147483647
    
    match {
      versioned_expr = "SRC_IPS_V1"
      
      config {
        src_ip_ranges = ["*"]
      }
    }
    
    description = "Default allow rule"
  }
}

# Attach security policy to backend services
resource "google_compute_backend_service_iam_binding" "api_gateway_policy" {
  backend_service = google_compute_backend_service.api_gateway.name
  role            = "roles/compute.securityAdmin"
  members         = ["serviceAccount:${var.project_id}@cloudservices.gserviceaccount.com"]
}

# Outputs
output "load_balancer_ip" {
  value       = google_compute_global_address.lb_ip.address
  description = "Load balancer IP address"
}

output "load_balancer_url" {
  value       = "https://${var.domain_name}"
  description = "Load balancer URL"
}

output "ssl_certificate_status" {
  value       = google_compute_managed_ssl_certificate.lb_cert.managed[0].status
  description = "SSL certificate provisioning status"
}
