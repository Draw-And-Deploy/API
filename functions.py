import classes
import textwrap

def resource_group_script(rg: classes.ResourceGroup):
    rg_script = textwrap.dedent(f'''

    # Creating Azure Resource Group 
    resource "azurerm_resource_group" "{rg.name}" {{
      name     = "{rg.name}"
      location = "{rg.location}"
    }}''')
    return rg_script


def security_group_script(sg: classes.SecurityGroup):
    sg_script = textwrap.dedent(f'''
    # Creating Network Security Group
    resource "azurerm_network_security_group" "{sg.name}" {{
      name                = "{sg.name}"
      location            = azurerm_resource_group.{sg.rg}.location
      resource_group_name = azurerm_resource_group.{sg.rg}.name
    }}

    locals {{
      {sg.rule_name}_{sg.rule_direction}_ports_map = {{
    ''')

    for i in range(len(sg.rule_dest_port_range_list)):
    	sg_script = sg_script + f'    "{sg.rule_priority_list[i]}" : "{sg.rule_dest_port_range_list[i]}", \n'

    sg_script = sg_script + textwrap.dedent(
    f'''  }}
    }}

    # Creating Network Security Rule
    resource "azurerm_network_security_rule" "{sg.rule_name}" {{
      for_each = local.{sg.rule_name}_{sg.rule_direction}_ports_map
      name                        = "Rule-Port-${{each.value}}"
      priority                    = each.key
      direction                   = "{sg.rule_direction}"
      access                      = "{sg.rule_access}"
      protocol                    = "{sg.rule_protocol}"
      source_port_range           = "{sg.rule_source_port_range}"
      destination_port_range      = each.value
      source_address_prefix       = "{sg.rule_source_address_prefix}"
      destination_address_prefix  = "{sg.rule_dest_address_prefix}"
      resource_group_name         = azurerm_resource_group.{sg.rg}.name
      network_security_group_name = azurerm_network_security_group.{sg.name}.name
    }}
    ''')
    return sg_script


def virtual_network_script(vnet: classes.VirtualNetwork):
    vnet_script = textwrap.dedent(f'''

    # Creating Azure Virtual Network
    resource "azurerm_virtual_network" "{vnet.name}" {{
      name                = "{vnet.name}"
      location            = azurerm_resource_group.{vnet.rg}.location
      address_space       = ["{vnet.cidr_block}"]
      resource_group_name = azurerm_resource_group.{vnet.rg}.name
    }}
    ''')
    return vnet_script


def vnet_subnets_script(subnet: classes.Subnet):
    subnet_script = textwrap.dedent(f'''
    resource "azurerm_subnet" "{subnet.name}" {{
      name           = "{subnet.name}"
      resource_group_name  = azurerm_resource_group.{subnet.resource_group}.name
      virtual_network_name = azurerm_virtual_network.{subnet.vnet}.name
      address_prefixes = ["{subnet.cidrblock}"]
    }}
    ''')
    return subnet_script


def nat_gateway_script(nat_gtw: classes.NatGateway):
    nat_gtw_script = textwrap.dedent(f'''

    # Public IP for NAT Gateway
    resource "azurerm_public_ip" "{nat_gtw.name}-public-ip" {{
      name                = "{nat_gtw.name}-public-ip"
      location            = azurerm_resource_group.{nat_gtw.resource_group}.location
      resource_group_name = azurerm_resource_group.{nat_gtw.resource_group}.name
      allocation_method   = "Static"
      sku                 = "Standard"
      zones               = ["1"]
    }}

    # Public IP Prefix
    resource "azurerm_public_ip_prefix" "{nat_gtw.name}-public-ip-prefix" {{
      name                = "{nat_gtw.name}-public-ip-prefix"
      location            = azurerm_resource_group.{nat_gtw.resource_group}.location
      resource_group_name = azurerm_resource_group.{nat_gtw.resource_group}.name
      prefix_length       = 30
      zones               = ["1"]
    }}

    # Creating NAT Gateway
    resource "azurerm_nat_gateway" "{nat_gtw.name}" {{
      name                    = "{nat_gtw.name}"
      location                = azurerm_resource_group.{nat_gtw.resource_group}.location
      resource_group_name     = azurerm_resource_group.{nat_gtw.resource_group}.name
      sku_name                = "Standard"
      idle_timeout_in_minutes = 10
      zones                   = ["1"]
    }}

    # Associating NAT Gateway to Public IP
    resource "azurerm_nat_gateway_public_ip_association" "{nat_gtw.name}-public-ip" {{
      nat_gateway_id       = azurerm_nat_gateway.{nat_gtw.name}.id
      public_ip_address_id = azurerm_public_ip.{nat_gtw.name}-public-ip.id
    }}

    # Associating NAT Gateway to Public IP Prefix
    resource "azurerm_nat_gateway_public_ip_prefix_association" "{nat_gtw.name}" {{
      nat_gateway_id      = azurerm_nat_gateway.{nat_gtw.name}.id
      public_ip_prefix_id = azurerm_public_ip_prefix.{nat_gtw.name}-public-ip-prefix.id
    }}
    ''')
    return nat_gtw_script


def virtual_machine_script(vm: classes.VirtualMachine, username):
    vm_script = textwrap.dedent(f'''

    # VM Public IP
    resource "azurerm_public_ip" "{vm.name}-public-ip" {{
      name                = "{vm.name}-public-ip"
      resource_group_name = azurerm_resource_group.{vm.rg}.name
      location            = azurerm_resource_group.{vm.rg}.location
      allocation_method   = "Dynamic"
    }}
    
    # Network Interface for VM
    resource "azurerm_network_interface" "{vm.nic}" {{
      name                = "{vm.nic}-nic"
      location            = azurerm_resource_group.{vm.rg}.location
      resource_group_name = azurerm_resource_group.{vm.rg}.name
      ip_configuration {{
        name                          = "{vm.name}-ip-config"
        subnet_id                     = azurerm_subnet.{vm.subnet}.id
        private_ip_address_allocation = "Dynamic"
        public_ip_address_id = azurerm_public_ip.{vm.name}-public-ip.id
      }}
    }}
    
    # Creating Virtual Machine
    resource "azurerm_virtual_machine" "{vm.name}" {{
      name                  = "{vm.name}"
      location              = azurerm_resource_group.{vm.rg}.location
      resource_group_name   = azurerm_resource_group.{vm.rg}.name
      network_interface_ids = [azurerm_network_interface.{vm.nic}.id]
      vm_size               = "Standard_DS1_v2"
      storage_image_reference {{
        publisher = "{vm.image[0]}"
        offer     = "{vm.image[1]}"
        sku       = "{vm.image[2]}"
        version   = "{vm.image[3]}"
      }}

      storage_os_disk {{
        name              = "{vm.name}-osdisk"
        caching           = "ReadWrite"
        create_option     = "FromImage"
        managed_disk_type = "Standard_LRS"
      }}

      os_profile {{
        computer_name  = "{vm.hostname}"
        admin_username = "{vm.username}"
        admin_password = "{vm.password}"
      }}
    
      os_profile_linux_config {{
        disable_password_authentication = false
      }}

      tags = {{
          name = "{vm.name}"
      }}
    ''')

    # if vm.public_key != None:
    # 	vm_script = vm_script + textwrap.dedent(f'''
    #   os_profile_linux_config {{
    #     disable_password_authentication = true
    #     admin_username      = "{vm.username}"
    #     admin_ssh_key {{
    #       username = ""
    #       public_key = file("/terraform_api_dirs/{username}/ssh_keys/key_{vm.public_key}")
    #     }}
    #   }}
    # ''')
    
    if vm.custom_data != None:
    	vm_script = vm_script + f'  custom_data = filebase64("{vm.custom_data}") \n'
    vm_script = vm_script + '}'

    return vm_script