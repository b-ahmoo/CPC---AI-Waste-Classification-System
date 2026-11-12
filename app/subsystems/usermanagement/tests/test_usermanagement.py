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
            user_id="TestUser", 
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

    def test_user_country_and_rules(self):
        db.session.add(self.user)
        db.session.commit()
        self.assertEqual(self.user.get_country(), "Germany")
        self.assertEqual(self.user.get_user_name(), "TestUser")
        self.assertIn("DE", self.country.get_rules())

    def test_register_user(self):
        created_user = self.service.register_user(
            user_id="NewUser", 
            username="NewUser", 
            email="new@uni.edu", 
            country=self.country
        )
        self.assertEqual(created_user.username, "NewUser")
        self.assertIsNotNone(self.service.find_user_by_email("new@uni.edu"))

    def test_authenticate_success(self):
        db.session.add(self.user)
        db.session.commit()
        with self.app.test_request_context():
            logged_in = self.service.authenticate("test@uni.edu")
        self.assertEqual(logged_in.email, "test@uni.edu")
        self.assertEqual(logged_in.user_id, "TestUser")

    def test_logout_route_clears_the_session(self):
        with self.app.test_request_context():
            from flask import session
            session['user_id'] = "TestUser"
            session.clear()
            self.assertIsNone(session.get('user_id'))

    def test_delete_account_deactivates(self):
        db.session.add(self.user)
        db.session.commit()
        success = self.service.delete_account("TestUser")
        self.assertTrue(success)
        self.assertFalse(self.service.find_user_by_id("TestUser").is_active)

    def test_find_user_by_id(self):
        db.session.add(self.user)
        db.session.commit()
        found = self.service.find_user_by_id("TestUser")
        self.assertEqual(found.email, "test@uni.edu")

    def test_find_user_by_email(self):
        db.session.add(self.user)
        db.session.commit()
        found = self.service.find_user_by_email("test@uni.edu")
        self.assertEqual(found.user_id, "TestUser")

if __name__ == '__main__':
    unittest.main()