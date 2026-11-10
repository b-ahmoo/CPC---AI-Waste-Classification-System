
import unittest
import app.models.usermanagement_models
import app.subsystems.usermanagement.usermanagement
import app.subsystems.usermanagement.exceptions


class TestUserManagementSubsystem(unittest.TestCase):

    def setUp(self):
        """Initialize fresh service and sample objects before each test."""
        self.service = app.subsystems.usermanagement.usermanagement.AccountService()
        self.country = app.models.usermanagement_models.Country(country_id="c1", name="Germany", code="DE")
        self.user = self.service.create_account("u1", "Sejal", "sejal@uni.edu", self.country)

    # 1. Country Model Initialization
    def test_country_initialization(self):
        self.assertEqual(self.country.name, "Germany")
        self.assertEqual(self.country.code, "DE")

    # 2. Country Details Serialization
    def test_country_get_details(self):
        details = self.country.get_details()
        self.assertEqual(details["country_id"], "c1")
        self.assertEqual(details["code"], "DE")

    # 3. User Model Initialization
    def test_user_initialization(self):
        self.assertEqual(self.user.username, "Sejal")
        self.assertEqual(self.user.email, "sejal@uni.edu")
        self.assertTrue(self.user.is_active)

    # 4. User Serialization
    def test_user_to_dict(self):
        data = self.user.to_dict()
        self.assertEqual(data["user_id"], "u1")
        self.assertEqual(data["country"]["name"], "Germany")

    # 5. Account Service Create Account Success
    def test_create_account_success(self):
        new_user = self.service.create_account("u2", "Alex", "alex@uni.edu", self.country)
        self.assertEqual(new_user.username, "Alex")

    # 6. Duplicate User ID Exception
    def test_create_account_duplicate_id(self):
        with self.assertRaises(app.subsystems.usermanagement.exceptions.DuplicateUserError):
            self.service.create_account("u1", "Different", "diff@uni.edu", self.country)

    # 7. Duplicate Email Exception
    def test_create_account_duplicate_email(self):
        with self.assertRaises(app.subsystems.usermanagement.exceptions.DuplicateUserError):
            self.service.create_account("u3", "Different", "sejal@uni.edu", self.country)

    # 8. Invalid Email Format Exception
    def test_create_account_invalid_email(self):
        with self.assertRaises(app.subsystems.usermanagement.exceptions.InvalidEmailFormatError):
            self.service.create_account("u4", "BadEmail", "invalid-email", self.country)

    # 9. Deactivate Account Success
    def test_deactivate_user_account(self):
        self.service.deactivate_user_account("u1")
        self.assertFalse(self.user.is_active)

    # 10. Find User By ID Success & Failure
    def test_find_user_by_id(self):
        found = self.service.find_user_by_id("u1")
        self.assertEqual(found, self.user)
        not_found = self.service.find_user_by_id("u999")
        self.assertIsNone(not_found)

    # 11. Find User By Email Success
    def test_find_user_by_email_success(self):
        found = self.service.find_user_by_email("sejal@uni.edu")
        self.assertIsNotNone(found)

    # 12. Login Success for Active User
    def test_login_success(self):
        logged_in = self.service.login("sejal@uni.edu")
        self.assertEqual(logged_in.user_id, "u1")

    # 13. Login Failure with Non-Existent Email (Raises UserNotFoundError)
    def test_login_user_not_found_exception(self):
        with self.assertRaises(app.subsystems.usermanagement.exceptions.UserNotFoundError):
            self.service.login("ghost@uni.edu")

    # 14. Login Failure with Inactive User (Raises InactiveUserError)
    def test_login_inactive_user_exception(self):
        self.service.deactivate_user_account("u1")
        with self.assertRaises(app.subsystems.usermanagement.exceptions.InactiveUserError):
            self.service.login("sejal@uni.edu")

    # 15. Cross-Subsystem Waste Integration Rules
    def test_waste_integration_guidelines(self):
        regulations = app.subsystems.usermanagement.usermanagement.WasteIntegration.get_user_waste_regulations(self.user)
        self.assertIn("Germany", regulations["applicable_country"])
        self.assertEqual(regulations["user"], "Sejal")


if __name__ == "__main__":
    unittest.main()
