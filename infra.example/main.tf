terraform {
  required_version = ">= 1.5"
  required_providers {
    aiven = {
      source  = "aiven/aiven"
      version = "~> 4.0"
    }
  }
}

provider "aiven" {
  api_token = var.aiven_api_token
}

resource "aiven_pg" "amf" {
  project      = var.aiven_project
  service_name = var.service_name
  cloud_name   = "do-nyc"
  plan         = var.plan

  termination_protection = true

  pg_user_config {
    pg_version = var.pg_version
  }
}
