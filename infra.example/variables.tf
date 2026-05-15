variable "aiven_api_token" {
  description = "Aiven personal API token. Provide via TF_VAR_aiven_api_token."
  type        = string
  sensitive   = true
}

variable "aiven_project" {
  description = "Aiven project that owns the service."
  type        = string
  default     = "jay-miller"
}

variable "service_name" {
  description = "Aiven service name. Must be unique within the project."
  type        = string
  default     = "amf-pg"
}

variable "plan" {
  description = "Aiven for PostgreSQL plan. 'hobbyist' is the dev tier (single node, do-nyc only)."
  type        = string
  default     = "hobbyist"
}
