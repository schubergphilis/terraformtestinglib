# azurerm_virtual_machine
# aws_instance

resource "aws_instance" "node1" {

    tags = {
        Name = "custsasdfsf015-node01"
        skip_positioning = "true"
        skip-linting = "true"
    }
}


resource "aws_instance" "node2" {
    tags = {
        Name = "custsfgssgfa015-node01"
    }
}

resource "aws_instance" "node7" {
    tags = {
        Name = "node"
    }
}
