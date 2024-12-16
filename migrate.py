import requests
import config

source_headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
}

destination_headers = {
    "Authorization": f"token {config.DESTINATION_API_KEY}:{config.DESTINATION_API_SECRET}",
    "Content-Type": "application/json",
}


def login_to_source(base_url, username, password):
    login_url = f"{base_url}/api/method/login"
    payload = {"usr": username, "pwd": password}

    response = requests.post(login_url, data=payload)
    if response.status_code == 200:
        print(f"Logged in successfully!")
        return response.cookies
    else:
        raise Exception(f"Login failed: {response.text}")


def fetch_document_list(doctype, cookies):
    """Fetch the list of document names from the source Frappe instance."""
    response = requests.get(f"{config.SOURCE_URL}/api/resource/{doctype}", cookies=cookies, params=config.params)
    if response.status_code == 200:
        return [entry["name"] for entry in response.json().get("data", [])]
    else:
        print(
            f"Failed to fetch list. Status Code: {response.status_code}, Response: {response.text}"
        )
        return []


def fetch_data(doctype, name, cookies):
    """Fetch a specific document's data from the source Frappe instance."""
    response = requests.get(
        f"{config.SOURCE_URL}/api/resource/{doctype}/{name}", headers=source_headers, cookies=cookies
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
        f"{config.DESTINATION_URL}/api/resource/{doctype}",
        headers=destination_headers,
        json={"data": data},
    )
    if response.status_code == 200:
        print(f"Successfully sent record: {data.get("name")}")
    else:
        print(
            f"Failed to send record: {data.get("name")}. Status Code: {response.status_code}, Response: {response.text}"
        )


if __name__ == "__main__":
    print("Fetching list of document names from source...")
    source_cookies = login_to_source(config.SOURCE_URL, config.SOURCE_USERNAME, config.SOURCE_PASSWORD)
    names = fetch_document_list(doctype=config.doctype, cookies=source_cookies)

    if names:
        print(f"Fetched {len(names)} document names:\n {names}")
        for name in names:
            data = fetch_data(doctype=config.doctype, name=name, cookies=source_cookies)
            # print(data)
            if data:
                data["supplier_type"]="Company"
                send_data(doctype=config.doctype, data=data)
            else:
                print(f"Skipping {name} due to fetch error.")
    else:
        print("No document names to process.")
