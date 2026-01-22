resource "azurerm_resource_group" "rg" {
  name     = "${rg_name}"
  location = "${location}"
}

resource "azurerm_storage_account" "stg" {
  name                     = "${storage_account_name}"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  # ✅ Microsoft cloud security benchmark compliant
  enable_https_traffic_only       = true
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false

  # Prevent shared key access (audit policy)
  shared_access_key_enabled = false
}
