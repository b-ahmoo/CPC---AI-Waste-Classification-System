import pytest
from app import create_app
from app.extensions import db

@pytest.fixture
def app():
    # 1. Create a Flask app configured for testing
    app = create_app()
    app.config.update({
        "TESTING": True,
        # Use a temporary in-memory SQLite database for fast, isolated tests
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })

    # 2. Build the database structure before tests run
    with app.app_context():
        db.create_all()
        yield app
        
        # Tear down the database after tests complete
        # db.session.remove()
        # db.drop_all()

@pytest.fixture
def client(app):
    """Provides a simulated web browser to test your routes."""
    return app.test_client()