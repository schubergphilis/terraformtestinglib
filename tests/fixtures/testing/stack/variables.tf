variable "value" {
    default = "interpolated_value"
}
variable "empty_value" {}

variable "map_variable" {

    default = {
        us-east-1 = "image-1234"
        us-west-2 = "image-4567"
    }
}

variable "zones" {
    default = [
        "us-east-1a",
        "us-east-1b"]
}
