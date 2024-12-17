from dotenv import load_dotenv
import os

load_dotenv()


class Source:
    url = os.getenv('SOURCE_URL')
    username = os.getenv("SOURCE_USERNAME")
    password = os.getenv("SOURCE_PASSWORD")
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


class Destination:
    url = os.getenv("DESTINATION_URL")
    api_key = os.getenv("DESTINATION_API_KEY")
    api_secret = os.getenv("DESTINATION_API_SECRET")
    headers = {
        "Authorization": f"token {os.getenv('DESTINATION_API_KEY')}:{os.getenv('DESTINATION_API_SECRET')}",
        "Content-Type": "application/json",
    }


doctype = "Account"
# params = {
#     "filters": '[["status", "=", "Active"]]',
#     "fields": '["name", "employee_name", "status"]',
#     "limit_page_length": 50,
#     "limit_start": 0,
#     "order_by": "employee_name asc",
# }
root_accounts = [
    "10000 Application of Funds (Assets) - AHS",
    "30000 Income - AHS",
    "40000 Expenses - AHS",
    "20000 Source of Funds (Liabilities) - AHS",
]
params = {
    "Supplier": {
        "filters": '[["supplier_type","=","VAT Registered"]]',
        "limit_page_length": 400,
        "limit_start": 0,
    },
    "Item": {},
}
