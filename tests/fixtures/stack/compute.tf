
resource "azurerm_virtual_machine" "node3" {
  name                = "custsxfgbngz015-node02"

  tags = {
    skip_linting = "true"
  }
}

resource "azurerm_virtual_machine" "node4" {
  name                = "custsxfgbngz015-node02"

  tags = {
    skip_linting = "true"
  }
}

resource "azurerm_virtual_machine" "node5" {
  name                = "custsxfgbngz015-node02"

  tags = {
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
