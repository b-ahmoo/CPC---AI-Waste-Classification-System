import unittest
from flask import Flask
from app import db
import app.subsystems.usermanagement.usermanagement
import app.models.usermanagement_models

class TestUserManagementSubsystem(unittest.TestCase):
    def setUp(self):
        """Initialize fresh service and sample objects before each test."""
        self.app = Flask(__name__)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        self.app.config['SECRET_KEY'] = 'test-key'
        
        db.init_app(self.app)
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        db.create_all()
        
        self.service = app.subsystems.usermanagement.usermanagement.AccountService()
        
        # Fixed: Using keyword arguments for SQLAlchemy db.Model classes
        self.country = app.models.usermanagement_models.Country(
            country_id="c1", 
            name="Germany", 
            code="DE"
        )
        db.session.add(self.country)
        db.session.commit()

        self.user = app.models.usermanagement_models.User(
            user_id="u1", 
            username="TestUser", 
            email="test@uni.edu", 
            country=self.country
        )

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_country_initialization(self):
        self.assertEqual(self.country.country_id, "c1")
        self.assertEqual(self.country.name, "Germany")
        self.assertEqual(self.country.code, "DE")

    def test_country_get_details(self):
        self.assertEqual(self.country.name, "Germany")

    def test_waste_integration_guidelines(self):
        rules = app.subsystems.usermanagement.usermanagement.WasteIntegration.get_user_waste_regulations(self.user)
        self.assertIn("Germany", rules["applicable_country"])
        self.assertEqual(rules["user"], "TestUser")

    def test_create_account(self):
        created_user = self.service.create_account(
            user_id="u2", 
            username="NewUser", 
            email="new@uni.edu", 
            country=self.country
        )
        self.assertEqual(created_user.username, "NewUser")
        self.assertIsNotNone(self.service.find_user_by_email("new@uni.edu"))

    def test_login_success(self):
        db.session.add(self.user)
        db.session.commit()
        logged_in = self.service.login("test@uni.edu")
        self.assertEqual(logged_in.email, "test@uni.edu")

    def test_logout(self):
        db.session.add(self.user)
        db.session.commit()
        result = self.service.logout("u1")
        self.assertTrue(result)

    def test_deactivate_account(self):
        db.session.add(self.user)
        db.session.commit()
        success = self.service.deactivate_user_account("u1")
        self.assertTrue(success)
        self.assertFalse(self.service.find_user_by_id("u1").is_active)

    def test_find_user_by_id(self):
        db.session.add(self.user)
        db.session.commit()
        found = self.service.find_user_by_id("u1")
        self.assertEqual(found.email, "test@uni.edu")

    def test_find_user_by_email(self):
        db.session.add(self.user)
        db.session.commit()
        found = self.service.find_user_by_email("test@uni.edu")
        self.assertEqual(found.user_id, "u1")

if __name__ == '__main__':
    unittest.main()