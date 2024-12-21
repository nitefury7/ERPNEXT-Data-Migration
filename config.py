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

doctypes = ["Journal Entry","Supplier","Student","Item", "Purchase Invoice", "Purchase Order", "Purchase Receipt", "User", "Print Format"]

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
        "filters": '[["name","=","Santinagar Footsal"]]',
        "limit_page_length": 500,
        "limit_start": 0,
        "order_by": "creation desc",
    },
    "Item": {
        # "filters": '[["","=",""]]',
        "limit_page_length": 400,
        "limit_start": 0,
    },
    "Customer": {
        # "filters": '[["","=",""]]',
        "limit_page_length": 4000,
        "limit_start": 0,
    },
    "User": {
        # "filters": '[["user_type","=","System User"]]',
        "limit_page_length": 100,
        "limit_start": 0,
    },
    "Purchase Invoice": {
        "filters": '[["name","=","PINV-00363"]]',
        # "filters": '[["status","=","Draft"]]',
        "limit_page_length": 3000,
        "limit_start": 0,
        "order_by": "creation asc",
    },
    "Purchase Order": {
        # "filters": '[["","=",""]]',
        # "filters": '[["status","!=","Draft"],["status","!=","Cancelled"]]',
        "limit_page_length": 100,
        "limit_start": 2,
        "order_by": "creation asc",
    },
    "Purchase Receipt": {
        # "filters": '[["status","=",""]]',
        # "filters": '{"status":["in",["Cancelled","Draft"]]}',
        "limit_page_length": 10,
        "limit_start": 50,
        "order_by": "creation asc",
    },
}

domain = "ace.edu.np"
