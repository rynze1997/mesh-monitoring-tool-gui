import dearpygui.dearpygui as dpg
import os
from network.actions import AuthHandler
import json

authentication_handler = AuthHandler()
def create_authentication_tab():
    with dpg.menu(label="Authentication", tag="__auth_menu"):
        dpg.add_combo(label="Select Server", items=["STAGE", "PROD", "DEV", "EDGE"], 
                      default_value="STAGE", tag="__server_dropdown", callback=server_changed_callback)
        
        dpg.add_text("Login details:")
        # Email and password input fields. If server is changed, reset the login fields and Site dropdown menu
        dpg.add_input_text(label="Email", source="string_value", tag="__email_text", callback=input_modified_callback)
        dpg.add_input_text(label="Password", source="string_value", tag="__password_text", password=True, callback=input_modified_callback)
        
        dpg.add_button(label="Login", tag="__login_button", callback=lambda: authentication_handler.execute_login(
            {"username": dpg.get_value("__email_text"), "password": dpg.get_value("__password_text"), "server": dpg.get_value("__server_dropdown")}
            , on_login_success, on_login_failure ))
        dpg.add_text("", tag="__login_text")

        # Hidden dropdown menu for site selection, to be shown after successful login
        dpg.add_combo(label="Select Site", tag="__site_dropdown", show=False, callback=on_site_selected)
        
def get_cleaned_site_name(site, disallowed):
    return "".join([c for c in site if not c in disallowed])

def process_site(site, site_name, disallowed):
    site_data = authentication_handler.getSiteData(site)
    site = site_data['title']
    devices_json = authentication_handler.getSiteIndices(site)
    site_name.append(site)
    
    # Write devices_json to JSON file adding site name and security keys
    devices_json['cryptoKey'] = site_data['keyStr']
    devices_json['accessAddr'] = site_data['addrStr']
    devices_json['siteName'] = site
    with open(f"./.auth/{site}.json", 'w') as file:
        json.dump(devices_json, file, indent=4)

def on_site_selected(sender):
    selected_item = dpg.get_value(sender)
    print(f"Selected item: {selected_item}")
    
    dropdown_config = dpg.get_item_configuration(sender)
    all_items = dropdown_config.get("items", [])
    print(f"All items in the dropdown: {all_items}")
    
    if not os.path.exists("./.auth"):
        os.mkdir("./.auth")
    
    site_name = []
    disallowed = ["\\", "/", " ", "^", "|"]
    
    if selected_item == "ALL":
        for site in all_items[1:]:
            process_site(site, site_name, disallowed)
    else:
        process_site(selected_item, site_name, disallowed)
        
    dpg.configure_item("sites", items=site_name)

def server_changed_callback():
    # Reset email and password fields
    dpg.set_value("__email_text", "")
    dpg.set_value("__password_text", "")

    # Hide the site dropdown and reset its value
    dpg.hide_item("__site_dropdown")
    dpg.set_value("__site_dropdown", [])

    # Clear any login status messages
    dpg.set_value("__login_text", "Server changed, please login again.")
    
def input_modified_callback():
    # Hide the dropdown menu
    dpg.hide_item("__site_dropdown")
    # Reset login text
    dpg.set_value("__login_text", "")
    
def on_login_success():
    dpg.set_value("__login_text", "Login successful!")
    site_names = authentication_handler.getSiteNames()
    dpg.configure_item("__site_dropdown", items=["ALL"] + site_names, show = True)
    
def on_login_failure():
    dpg.set_value("__login_text", "Could not log in. Probably invalid credentials")
