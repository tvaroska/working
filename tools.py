from datetime import date
from typing import Optional, Dict, List, Union
from langchain.tools import Tool
from pydantic import BaseModel, Field

# Keep existing data structures
USERS = [
    {'id': 1,
     'name': {'first': 'James', 'last': 'Smith'},
     'DOB': date(year=1982, month=5, day=8)},
    {'id': 2,
     'name': {'first': 'Sarah', 'last': 'Johnson'},
     'DOB': date(year=1985, month=3, day=15)},
    {'id': 3,
     'name': {'first': 'Michael', 'last': 'Chen'},
     'DOB': date(year=1990, month=7, day=22)},
    {'id': 4,
     'name': {'first': 'Elena', 'last': 'Rodriguez'},
     'DOB': date(year=1988, month=9, day=30)},
]

ACCOUNTS = [
    # James's accounts
    {'account_no': 6504876475938248,
     'user': 1,
     'type':'CREDIT',
    },
    {'account_no': 4948924115781567,
     'user': 1,
     'type':'CHECKING',
    },
    # Sarah's accounts
    {'account_no': 4532785612349087,
     'user': 2,
     'type':'CHECKING',
    },
    {'account_no': 6011456789012345,
     'user': 2,
     'type':'CREDIT',
    },
    {'account_no': 9876543210987654,
     'user': 2,
     'type':'SAVINGS',
    },
    # Michael's accounts
    {'account_no': 4539876543210123,
     'user': 3,
     'type':'CHECKING',
    },
    {'account_no': 5412345678901234,
     'user': 3,
     'type':'CREDIT',
    },
    # Elena's accounts
    {'account_no': 4916789012345678,
     'user': 4,
     'type':'CHECKING',
    },
    {'account_no': 6011987654321098,
     'user': 4,
     'type':'CREDIT',
    },
    {'account_no': 9870123456789012,
     'user': 4,
     'type':'SAVINGS',
    },
]

class UserIdentificationError(Exception):
    """Custom exception for user identification errors"""
    pass

def identify_user(
    first_name: str,
    last_name: str,
    credit_card_last_four: Optional[str] = None,
    account_last_four: Optional[str] = None
) -> Dict[str, int]:
    """
    Get user ID from user identification information.
    
    Args:
        first_name: User's first name
        last_name: User's last name
        credit_card_last_four: Last 4 digits of credit card number
        account_last_four: Last 4 digits of any account number

    Returns:
        Dict containing user ID if found

    Raises:
        UserIdentificationError: If validation fails or user not found
    """
    # Validate that at least one of the last four digits is provided
    if not credit_card_last_four and not account_last_four:
        raise UserIdentificationError(
            "Either credit_card_last_four or account_last_four must be provided"
        )

    # Validate format if credit card last four is provided
    if credit_card_last_four and not (credit_card_last_four.isdigit() and len(credit_card_last_four) == 4):
        raise UserIdentificationError(
            "credit_card_last_four must be exactly 4 digits"
        )

    # Validate format if account last four is provided
    if account_last_four and not (account_last_four.isdigit() and len(account_last_four) == 4):
        raise UserIdentificationError(
            "account_last_four must be exactly 4 digits"
        )

    # Find user by name first
    matching_user = None
    for user in USERS:
        if (user['name']['first'].lower() == first_name.lower() and 
            user['name']['last'].lower() == last_name.lower()):
            matching_user = user
            break
    
    if not matching_user:
        raise UserIdentificationError("User not found")

    # Get all user's accounts
    user_accounts = [acc for acc in ACCOUNTS if acc['user'] == matching_user['id']]
    
    # Check credit card last four if provided
    if credit_card_last_four:
        credit_accounts = [acc for acc in user_accounts if acc['type'] == 'CREDIT']
        for account in credit_accounts:
            if str(account['account_no'])[-4:] == credit_card_last_four:
                return {"user_id": matching_user['id']}

    # Check account last four if provided
    if account_last_four:
        non_credit_accounts = [acc for acc in user_accounts if acc['type'] in ['CHECKING', 'SAVINGS']]
        for account in non_credit_accounts:
            if str(account['account_no'])[-4:] == account_last_four:
                return {"user_id": matching_user['id']}
    
    raise UserIdentificationError("User not found")

def get_user_details(user_id: int) -> Dict[str, Union[Dict, List]]:
    """
    Get user details and their accounts based on user ID.

    Args:
        user_id: User ID to look up

    Returns:
        Dict containing user details and associated accounts

    Raises:
        UserIdentificationError: If user not found
    """
    # Find user by ID
    user = next((u for u in USERS if u['id'] == user_id), None)
    if not user:
        raise UserIdentificationError("User not found")
    
    # Get all accounts for the user
    user_accounts = [acc for acc in ACCOUNTS if acc['user'] == user_id]
    
    # Return user details with their accounts
    return {
        "user": {
            "id": user['id'],
            "name": user['name'],
            "DOB": user['DOB']
        },
        "accounts": user_accounts
    }

# Create LangChain tools
identify_user_tool = Tool(
    name="identify_user",
    description="""
    Identifies a user by their name and either the last 4 digits of their credit card or account number.
    Required: first_name, last_name, and EITHER credit_card_last_four OR account_last_four.
    Returns the user's ID if found.
    """,
    func=lambda args: identify_user(
        first_name=args["first_name"],
        last_name=args["last_name"],
        credit_card_last_four=args.get("credit_card_last_four"),
        account_last_four=args.get("account_last_four")
    )
)

get_user_details_tool = Tool(
    name="get_user_details",
    description="""
    Retrieves detailed information about a user and their accounts using their user ID.
    Required: user_id (integer)
    Returns user's personal information and all associated accounts.
    """,
    func=lambda user_id: get_user_details(int(user_id))
)

# List of all available tools
tools = [identify_user_tool, get_user_details_tool]
