variable "project_id" {
  description = "The project ID to deploy to"
  type        = string
}

variable "region" {
  description = "The region to deploy to"
  type        = string
  default     = "asia-northeast1"
}

variable "service_name" {
  description = "The name of the Cloud Run service"
  type        = string
}