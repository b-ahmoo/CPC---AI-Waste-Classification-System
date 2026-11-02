"""
Subsystem 1: User Creation & Account Management

"""

from typing import List, Optional

# Team Collaboration: Import Keshina's shared WasteRules class if needed
# from app.subsystems.waste_rules import WasteRules


class Country:
    """Represents country-specific location and regulatory metadata."""
    
    def __init__(self, country_id: str, name: str, code: str):
        self.country_id: str = country_id
        self.name: str = name
        self.code: str = code

    def get_details(self) -> dict:
        return {
            "country_id": self.country_id,
            "name": self.name,
            "code": self.code
        }


class User:
    """Represents a system user and their profile settings."""
    
    def __init__(self, user_id: str, username: str, email: str, country: Country):
        self.user_id: str = user_id
        self.username: str = username
        self.email: str = email
        self.country: Country = country
        self.is_active: bool = True

    def update_profile(self, username: Optional[str] = None, email: Optional[str] = None, country: Optional[Country] = None) -> None:
        if username:
            self.username = username
        if email:
            self.email = email
        if country:
            self.country = country

    def deactivate_account(self) -> None:
        self.is_active = False

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "country": self.country.name,
            "is_active": self.is_active
        }


class AccountService:
    """Service class handling account creation, user lookup, and account management operations."""
    
    def __init__(self):
        self._users: List[User] = []

    def create_account(self, user_id: str, username: str, email: str, country: Country) -> User:
        if self.find_user_by_id(user_id):
            raise ValueError(f"Account with ID {user_id} already exists.")
        if self.find_user_by_email(email):
            raise ValueError(f"Account with email {email} already exists.")
        
        new_user = User(user_id=user_id, username=username, email=email, country=country)
        self._users.append(new_user)
        return new_user

    def find_user_by_id(self, user_id: str) -> Optional[User]:
        for user in self._users:
            if user.user_id == user_id:
                return user
        return None

    def find_user_by_email(self, email: str) -> Optional[User]:
        for user in self._users:
            if user.email.lower() == email.lower():
                return user
        return None

    def list_active_users(self) -> List[dict]:
        return [user.to_dict() for user in self._users if user.is_active]
