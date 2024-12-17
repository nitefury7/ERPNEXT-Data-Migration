import requests
import config
from config import Source, Destination


def login_to_source(base_url, username, password):
    login_url = f"{base_url}/api/method/login"
    payload = {"usr": username, "pwd": password}

    response = requests.post(login_url, data=payload)
    if response.status_code == 200:
        print(f"Logged in successfully!")
        return response.cookies
    else:
        raise Exception(f"Login failed: {response.text}")

cookies = login_to_source(Source.url, Source.username, Source.password)

def fetch_document_list(doctype):
    """Fetch the list of document names from the source Frappe instance."""
    params = config.params[doctype] if doctype in config.params else {}
    response = requests.get(f"{Source.url}/api/resource/{doctype}", cookies=cookies, params=params)
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
        f"{Source.url}/api/resource/{doctype}/{name}", headers=Source.headers, cookies=cookies
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
        print(f"Successfully sent record: {data.get("name")}")
    else:
        print(
            f"Failed to send record: {data.get("name")}. Status Code: {response.status_code}, Response: {response.text}"
        )


def build_tree(root_accounts):
    """Recursively build a tree structure for the chart of accounts."""
    def fetch_accounts(parent_account):
        params = {"filters": f'[["parent_account", "=", "{parent_account}"]]'}
        response = requests.get(
            f"{config.SOURCE_URL}/api/resource/Account", cookies=cookies, params=params
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


if __name__ == "__main__":
    # main()
    tree_demo()
