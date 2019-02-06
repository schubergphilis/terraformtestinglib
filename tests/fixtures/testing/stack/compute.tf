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


resource "resource_with_length_method" "interpolating_length" {
    policy = "${length(var.numbers)}"
}


resource "resource_with_list_attributes" "listed_resource" {
    os_profile_windows_config = {
        winrm {
            protocol = "HTTP"
        }
        additional_unattend_config {
            pass = "oobeSystem"
            component = "Microsoft-Windows-Shell-Setup"
            setting_name = "AutoLogon"
            content = "content1"
        }
        additional_unattend_config {
            pass = "oobeSystem"
            component = "Microsoft-Windows-Shell-Setup"
            setting_name = "FirstLogonCommands"
            content = "content2"
        }
    }
}
