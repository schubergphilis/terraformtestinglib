terraform {
    backend "s3" {
        bucket = "state"
        key = "whatever/key"
        region = "eu-west-1"
        encrypt = true
        dynamodb_table = "state-locking"
    }
}


data "vault_generic_secret" "default_administrator" {
    path = "env/pipeline/default_administrator"
}

data "terraform_remote_state" "platform" {
    backend = "s3"

    config {
        bucket = "state"
        key = "test/terraform.state"
        region = "eu-west-1"
        encrypt = true
        dynamodb_table = "state-locking"
    }
}
