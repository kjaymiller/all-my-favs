output "database_url" {
  description = "libpq-style connection URI for the amf database."
  value       = aiven_pg.amf.service_uri
  sensitive   = true
}
