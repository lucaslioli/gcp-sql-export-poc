variable "project" {}

variable "credentials_file" {}

variable "db_user" {}

variable "db_password" {}

variable "bucket_file" {}

variable "bucket_name" {}

variable "workflow_names" {
  type = list(string)
}

variable "region" {
  default = "us-central1"
}

variable "zone" {
  default = "us-central1-c"
}
