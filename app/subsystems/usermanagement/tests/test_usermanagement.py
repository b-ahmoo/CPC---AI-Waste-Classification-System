import unittest
import app.models.usermanagement_models
import app.subsystems.usermanagement.usermanagement
import app.subsystems.usermanagement.exceptions



class TestUserManagementSubsystem(unittest.TestCase):

    def setUp(self):
        """Initialize fresh service and sample objects before each test."""
        self.service = app.subsystems.usermanagement.usermanagement.AccountService()
        self.country = app.models.usermanagement_models.Country("c1", "Germany", "DE")
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
        self.assertTrue(self.user.is_active)
        self.assertEqual(self.user.username, "Sejal")

    # 4. User Profile Update
    def test_user_profile_update(self):
        self.user.update_profile(username="SejalD")
        self.assertEqual(self.user.username, "SejalD")

    # 5. User Account Deactivation Model Method
    def test_user_model_deactivation(self):
        self.user.deactivate_account()
        self.assertFalse(self.user.is_active)

    # 6. User Dictionary Serialization
    def test_user_to_dict(self):
        data = self.user.to_dict()
        self.assertEqual(data["email"], "sejal@uni.edu")
        self.assertEqual(data["country"]["name"], "Germany")

    # 7. Account Creation Service Success
    def test_create_account_success(self):
        new_country = app.models.usermanagement_models.Country("c2", "France", "FR")
        new_user = self.service.create_account("u2", "Alex", "alex@uni.edu", new_country)
        self.assertEqual(new_user.user_id, "u2")

    # 8. Duplicate Email Exception Handling
    def test_duplicate_email_exception(self):
        new_country = app.models.usermanagement_models.Country("c2", "France", "FR")
        with self.assertRaises(app.subsystems.usermanagement.exceptions.DuplicateEmailError):
            self.service.create_account("u2", "Duplicate", "sejal@uni.edu", new_country)

    # 9. Find User By ID Success
    def test_find_user_by_id_success(self):
        found = self.service.find_user_by_id("u1")
        self.assertEqual(found.username, "Sejal")

    # 10. Find User By ID Missing (None)
    def test_find_user_by_id_missing(self):
        found = self.service.find_user_by_id("invalid_id")
        self.assertIsNone(found)

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
