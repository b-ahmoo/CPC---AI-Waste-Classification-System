from database import initialize_database
from account_service import register_user, login_user


def main():
    initialize_database()

    print("=== Waste Recycling Assistant ===")

    print("\n1. Register")
    print("2. Login")

    choice = input("\nChoose an option: ")

    if choice == "1":
        username = input("Enter username: ")
        password = input("Enter password: ")
        country = input("Enter country: ")

        result = register_user(username, password, country)

        print(result["message"])

    elif choice == "2":
        username = input("Enter username: ")
        password = input("Enter password: ")

        result = login_user(username, password)

        if result["success"]:
            print("\nLogin successful!")
            print("User ID:", result["user_id"])
            print("Username:", result["username"])
            print("Country:", result["country"])
        else:
            print(result["message"])

    else:
        print("Invalid option.")


if __name__ == "__main__":
    main()