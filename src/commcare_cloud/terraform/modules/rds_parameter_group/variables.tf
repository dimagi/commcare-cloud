variable "name" {
  description = "Name of the DB parameter group"
  type        = string
}

variable "family" {
  description = "The family of the DB parameter group (e.g. postgres18)"
  type        = string
}

variable "description" {
  description = "Description of the DB parameter group"
  type        = string
  default     = ""
}

variable "parameters" {
  description = "List of DB parameter maps to apply"
  type = list(object({
    name         = string
    value        = string
    apply_method = string
  }))
  default = []
}

variable "tags" {
  description = "Tags to apply to the parameter group"
  type        = map(string)
  default     = {}
}
