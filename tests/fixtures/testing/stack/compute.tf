resource "azurerm_virtual_machine" "node3" {
    name = "custsxfgbngz015-node02"
    not_matching = "true"
    tags = {
        subattribute_test = "true"
        skip_linting = "true"
        name = "resource_name"
    }
}

resource "azurerm_virtual_machine" "node4" {
    name = "custsxfgbngz015-node02"
    valid_json = "{\"a\":\"2\"}"
    tags = {
        subattribute_test = "false"
        skip_linting = "true"
        name = "resource_name"
    }
}

resource "azurerm_virtual_machine" "node5" {
    name = "custsxfgbngz015-node02"
    tags = {
        name = "resource_name"
    }
}

resource "random_resource" "node6" {
    tags = {
        random = "value"
    }

}

resource "random_resource_other" "_node-_8" {
    tags = {
        random = "value"
    }

}

resource "resource_with_no_matching_rule" "node9" {
    tags = {
        random = "value"
    }

}


resource "broken_resource_with_multiple_tags" "node10" {
    tags = {
        random = "value"
    }

    tags = {
        broken = "true"
    }
}

resource "resource_with_variable" "node11" {
    tags = {
        variableized = "test_${var.value}"
    }
}


resource "resource_with_count" "node123-app0x" {
    count = 4
    ami = "${var.image-aws-rhel74}"
    tags = {
        Name = "${format("node1234-app%02d", count.index + 1)}"
    }
}
