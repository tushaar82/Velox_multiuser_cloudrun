# VPC Access Connector for Cloud Run

resource "google_vpc_access_connector" "connector" {
  name          = "trading-platform-connector"
  region        = var.region
  network       = google_compute_network.vpc.name
  ip_cidr_range = "10.8.0.0/28"
  
  min_throughput = 200
  max_throughput = 1000
  
  machine_type = "e2-micro"
}

output "vpc_connector_name" {
  value       = google_vpc_access_connector.connector.name
  description = "VPC Access Connector name"
}

output "vpc_connector_id" {
  value       = google_vpc_access_connector.connector.id
  description = "VPC Access Connector ID"
}
