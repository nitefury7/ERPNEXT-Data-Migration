import requests
import json
import config
from config import Source, Destination
import pickle
from logging.handlers import RotatingFileHandler
import logging
import os
from collections import defaultdict

def setup_logging(doctypes):
    loggers = defaultdict(dict)

    os.makedirs("logs", exist_ok=True)

    for doctype in doctypes:
        success_handler = RotatingFileHandler(
            f"logs/{doctype}_success.log",
            mode="a",
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
        )
        success_handler.setLevel(logging.INFO)

        success_logger = logging.getLogger(f"{doctype}_success")
        success_logger.setLevel(logging.INFO)
        success_logger.addHandler(success_handler)

        failure_handler = RotatingFileHandler(
            f"logs/{doctype}_failure.log",
            mode="a",
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
        )
        failure_handler.setLevel(logging.ERROR)

        failure_logger = logging.getLogger(f"{doctype}_failure")
        failure_logger.setLevel(logging.ERROR)
        failure_logger.addHandler(failure_handler)

        loggers[doctype]["success_logger"] = success_logger
        loggers[doctype]["failure_logger"] = failure_logger

    return loggers


def load_failed_records(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            return json.load(file)
    return {}
failed_records = load_failed_records("failed_records.json")


def save_failed_records(file_path, failed_records):
    with open(file_path, "w") as file:
        json.dump(failed_records, file, indent=4)


def save_cookies(requests_cookiejar, filename):
    with open(filename, "wb") as f:
        pickle.dump(requests_cookiejar, f)


def load_cookies(filename):
    with open(filename, "rb") as f:
        return pickle.load(f)


def login_to_source(base_url, username, password):
    login_url = f"{base_url}/api/method/login"
    payload = {"usr": username, "pwd": password}

    response = requests.post(login_url, data=payload)
    if response.status_code == 200:
        print(f"Logged in successfully!")
        save_cookies(response.cookies, "cookies.txt")
        return response.cookies
    else:
        raise Exception(f"Login failed: {response.text}")


def fetch_document_list(doctype, params=None):
    """Fetch the list of document names from the source Frappe instance."""
    if not params:
        params = config.params[doctype] if doctype in config.params else {}
    response = requests.get(f"{Source.url}/api/resource/{doctype}", cookies=load_cookies("cookies.txt"), params=params)
    if response.status_code == 200:
        return [entry["name"] for entry in response.json().get("data", [])]
    else:
        print(
            f"Failed to fetch list. Status Code: {response.status_code}, Response: {response.text}"
        )
        return []


def fetch_data(doctype, name):
    """Fetch a specific document's data from the source Frappe instance."""
    response = requests.get(
        f"{Source.url}/api/resource/{doctype}/{name}", headers=Source.headers, cookies=load_cookies("cookies.txt")
    )
    if response.status_code == 200:
        return response.json().get("data", {})
    else:
        print(
            f"Failed to fetch data for {name}. Status Code: {response.status_code}, Response: {response.text}"
        )
        return {}


def send_data(doctype, data):
    """Send a specific document's data to the destination Frappe instance."""
    response = requests.post(
        f"{Destination.url}/api/resource/{doctype}",
        headers=Destination.headers,
        json={"data": data},
    )
    if response.status_code == 200:
        loggers[doctype]["success_logger"].info(f"Successfully sent record: {data.get("name")}")
    else:
        loggers[doctype]["failure_logger"].error(
            f"Failed to send record: {data.get("name")}. Status Code: {response.status_code}, Response: {response.text}"
        )
        if response.status_code != 409:
            failed_records.setdefault(doctype, [])
            if data.get("name") not in failed_records[doctype]:
                failed_records[doctype].append(data.get("name"))

    save_failed_records("failed_records.json", failed_records)


def update_data(doctype, name, data):
    data.pop("modified", None)
    response = requests.put(
        f"{Destination.url}/api/resource/{doctype}/{name}",
        headers=Destination.headers,
        json={"data": data},
    )
    if response.status_code == 200:
        loggers[doctype]["success_logger"].info(f"Successfully updated record: {name}")
    else:
        loggers[doctype]["failure_logger"].error(
            f"Failed to update record: {data.get('name')}. Status Code: {response.status_code}, Response: {response.text}"
        )

def build_tree(root_accounts):
    def fetch_accounts(parent_account):
        params = {
            "filters": f'[["parent_account", "=", "{parent_account}"]]',
            "limit_page_length": 400,
            "limit_start": 0,
        }
        response = requests.get(
            f"{Source.url}/api/resource/Account", headers=Source.headers, cookies=load_cookies("cookies.txt"), params=params
        )
        if response.status_code == 200:
            return [entry["name"] for entry in response.json().get("data", [])]
        else:
            print(
                f"Failed to fetch accounts for {parent_account}. "
                f"Status Code: {response.status_code}, Response: {response.text}"
            )
            return []

    def build_subtree(parent_account):
        """Recursively build subtree for the given parent_account."""
        subtree = {}
        child_accounts = fetch_accounts(parent_account)
        for child in child_accounts:
            subtree[child] = build_subtree(child)
        return subtree

    tree = {}
    for root in root_accounts:
        tree[root] = build_subtree(root)

    return tree


def tree_demo():
    root_accounts = config.root_accounts

    chart_of_accounts_tree = build_tree(root_accounts)
    print(chart_of_accounts_tree)


def main():
    doctype = config.doctype
    names = fetch_document_list(doctype)

    if names:
        print(f"Fetched {len(names)} document names:\n {names}")
        for name in names:
            data = fetch_data(doctype=config.doctype, name=name)
            if data:
                send_data(doctype=config.doctype, data=data)
            else:
                print(f"Skipping {name} due to fetch error.")
    else:
        print("No document names to process.")


def send_coa(accounts, parent_name=None):
    for account_name, children in accounts.items():
        account_data = fetch_data("Account", account_name)
        if not account_data:
            print(f"Skipping {account_name} due to fetch failure.")
            continue

        if parent_name:
            account_data["parent"] = parent_name

        response = requests.post(
            f"{Destination.url}/api/resource/Account",
            headers=Destination.headers,
            json={"data":account_data},
        )
        if response.status_code == 200:
            print(
                f"Successfully added account: {account_name} under {parent_name or 'Root'}."
            )
        else:
            print(
                f"Failed to add account: {account_name} under {parent_name or 'Root'}. Response: {response.text}"
            )

        if isinstance(children, dict):
            send_coa(children, parent_name=account_name)


def send_chart_of_accounts():
    with open('accounts.json', 'r') as file:
        chart_of_accounts = json.load(file)
    send_coa(chart_of_accounts)

def send_suppliers():
    names = fetch_document_list("Supplier")
    for name in names:
        data = fetch_data(doctype="Supplier", name=name)
        if data:
            data["tax_category"] = data["supplier_type"] if data.get("supplier_type") else None
            data["tax_id"] = data["pan_no"] if data.get("pan_no") else None
            data["supplier_type"] = "Company" if data.get("supplier_type") else None
            
            send_data(doctype="Supplier", data=data)
        else:
            print(f"Skipping {name} due to fetch error.")


def send_students():
    names = fetch_document_list("Customer")
    for name in names:
        data = fetch_data(doctype="Customer", name=name)
        if data:
            customer_name = data["customer_name"]
            roll_no = data["roll_no"]

            name_parts = customer_name.split(" ")
            first_name = name_parts[0]
            last_name = name_parts[-1] if len(name_parts) > 1 else ""

            student_email = f"{first_name}_{last_name}_{roll_no}@{config.domain}".strip().lower()

            data["first_name"] = first_name
            data["last_name"] = last_name
            data["student_email_id"] = student_email
            data["joining_date"] = data["creation"]
        
            send_data(doctype="Student", data=data)
        else:
            print(f"Skipping {name} due to fetch error.")


def send_warehouses():
    names = fetch_document_list("Warehouse")
    for name in names:
        data = fetch_data(doctype="Warehouse", name=name)
        if data:
            send_data(doctype="Warehouse", data=data)
        else:
            print(f"Skipping {name} due to fetch error.")

def send_items():
    names = fetch_document_list("Item")
    for name in names:
        data = fetch_data(doctype="Item", name=name)
        if data:
            send_data(doctype="Item", data=data)
        else:
            print(f"Skipping {name} due to fetch error.")

def update_items():
    names = fetch_document_list("Item")
    for name in names:
        data = fetch_data(doctype="Item", name=name)
        if data:
            item_defaults = data.get("item_defaults", [])
            item_defaults.append({
                "default_warehouse": data.get("default_warehouse")
            })
            data = {
                "item_defaults": item_defaults
            }
            update_data(doctype="Item", name=name, data=data)
        else:
            print(f"Skipping {name} due to fetch error.")

def send_stock_ledger_entries():
    names = fetch_document_list("Stock Ledger Entry")
    for name in names:
        data = fetch_data(doctype="Stock Ledger Entry", name=name)
        if data:
            send_data(doctype="Stock Ledger Entry", data=data)
        else:
            print(f"Skipping {name} due to fetch error.")


def send_users():
    names = fetch_document_list("User")
    for name in names:
        if name == "Administrator" or name == "Guest":
            continue
        data = fetch_data(doctype="User", name=name)
        if data:
            data["creation"] = data["creation"]
            data["roles"] = data["user_roles"]
            send_data(doctype="User", data=data)
        else:
            print(f"Skipping {name} due to fetch error.")
def send_purchase_taxes_charges_template():
    names = fetch_document_list("Purchase Taxes and Charges Template")
    for name in names:
        data = fetch_data(doctype="Purchase Taxes and Charges Template", name=name)
        if data:
            send_data(doctype="Purchase Taxes and Charges Template", data=data)
        else:
            print(f"Skipping {name} due to fetch error.")

def send_fiscal_years():
    names = fetch_document_list("Fiscal Year")
    for name in names:
        data = fetch_data(doctype="Fiscal Year", name=name)
        if data:
            send_data(doctype="Fiscal Year", data=data)
        else:    
            print(f"Skipping {name} due to fetch error.")

def send_print_formats():
    names = fetch_document_list("Print Format")
    for name in names:
        data = fetch_data(doctype="Print Format", name=name)
        if data:
            send_data(doctype="Print Format", data=data)
        else:    
            print(f"Skipping {name} due to fetch error.")


def send_material_request():
    names = fetch_document_list("Material Request")
    for name in names:
        data = fetch_data(doctype="Material Request", name=name)
        if data:
            send_data(doctype="Material Request", data=data)
        else:
            print(f"Skipping {name} due to fetch error.")


def send_supplier_quotation():
    names = fetch_document_list("Supplier Quotation")
    for name in names:
        data = fetch_data(doctype="Supplier Quotation", name=name)
        if data:
            send_data(doctype="Supplier Quotation", data=data)
        else:
            print(f"Skipping {name} due to fetch error.")


def send_purchase_order():
    names = fetch_document_list("Purchase Order")
    for name in names:
        data = fetch_data(doctype="Purchase Order", name=name)
        if data:
            # data["scheduled_date"] = data.get("items", [{}])[0].get("scheduled_date")
            data["is_subcontracted"] = 0
            data.get("items", [{}])[0].pop("material_request_item", None)
            data.get("items", [{}])[0].pop("supplier_quotation_item", None)
            send_data(doctype="Purchase Order", data=data)
        else:
            print(f"Skipping {name} due to fetch error.")

def send_purchase_receipt():
    names = fetch_document_list("Purchase Receipt")
    for name in names:
        data = fetch_data(doctype="Purchase Receipt", name=name)
        if data:
            send_data(doctype="Purchase Receipt", data=data)
        else:
            print(f"Skipping {name} due to fetch error.")

def send_purchase_invoice():
    names = fetch_document_list("Purchase Invoice")
    for name in names:
        data = fetch_data(doctype="Purchase Invoice", name=name)
        if data:
            data["set_posting_time"] = 1
            for item in data.get("items", [{}]):
                item["uom"] = "Nos"
            send_data(doctype="Purchase Invoice", data=data)
        else:    
            print(f"Skipping {name} due to fetch error.")

def send_journal_entry():
    params = {
        # "filters": '[["status", "=", "Active"]]',
        "limit_page_length": 8000,
        "limit_start": 50396,
        "order_by": "creation asc",
    }
    names = fetch_document_list("Journal Entry", params=params)
    for name in names:
        data = fetch_data(doctype="Journal Entry", name=name)
        if data:
            accounts = data.get("accounts", [])
            for account in accounts:
                if account.get("party_type") == "Customer":
                    account["party_type"] = "Student"
            send_data(doctype="Journal Entry", data=data)
        else:    
            print(f"Skipping {name} due to fetch error.")


def send_failed_journal_entry():
    failed_je = failed_records.setdefault("Journal Entry", [])
    a = 0
    while a < len(failed_je):
        b = a + 200
        filters = json.dumps(
            [["name", "in", failed_je[a:b]], ["docstatus", "not in", ["0", "2"]]]
        )
        params = {
            "filters": filters,
            "limit_page_length": 56000,
            "limit_start": 0,
        }
        names = fetch_document_list("Journal Entry", params=params)
        a = b
        for name in names:
            data = fetch_data(doctype="Journal Entry", name=name)
            if data:
                accounts = data.get("accounts", [])
                for account in accounts:
                    if account.get("party_type") == "Customer":
                        account["party_type"] = "Student"

                send_data(doctype="Journal Entry", data=data)
            else:
                print(f"Skipping {name} due to fetch error.")


if __name__ == "__main__":
    loggers = setup_logging(config.doctypes)
    # cookies = login_to_source(Source.url, Source.username, Source.password)
    # main()
    # tree_demo()
    # send_chart_of_accounts()
    # send_suppliers()
    # send_warehouses()
    # send_items()
    # update_items()
    # send_students()
    # send_users()
    # send_purchase_taxes_charges_template()
    # send_fiscal_year()
    # send_print_formats() # doesnt work
    # send_material_request()
    # send_supplier_quotation()
    # send_purchase_order()
    # send_purchase_receipt()
    # send_purchase_invoice()
    # send_journal_entry()
    send_failed_journal_entry()
