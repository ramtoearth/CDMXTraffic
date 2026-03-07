"""
Unit tests for subscription logic

Requirements validated:
- 1.1: Unique subscriber creation
- 1.3: Duplicate email handling
- 1.4: Subscription reactivation
- 11.1: Unique unsubscribe token generation
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.subscribe.subscription_logic import (
    validate_and_save_subscriber,
    generate_unsubscribe_token,
    get_subscriber_by_email,
    save_subscriber_to_db
)
from src.shared.models import Subscriber


class TestGenerateUnsubscribeToken:
    """Test unsubscribe token generation"""
    
    def test_generates_non_empty_token(self):
        """Token should not be empty"""
        token = generate_unsubscribe_token()
        assert token
        assert len(token) > 0
    
    def test_generates_unique_tokens(self):
        """Each call should generate a unique token"""
        tokens = [generate_unsubscribe_token() for _ in range(100)]
        assert len(tokens) == len(set(tokens))


class TestValidateAndSaveSubscriber:
    """Test main subscription logic"""
    
    @patch('src.subscribe.subscription_logic.get_subscriber_by_email')
    @patch('src.subscribe.subscription_logic.save_subscriber_to_db')
    def test_creates_new_subscriber_with_valid_data(self, mock_save, mock_get):
        """Should create new subscriber when email doesn't exist"""
        # Setup mocks
        mock_get.return_value = None  # Email doesn't exist
        mock_save.return_value = True  # Save succeeds
        
        # Execute
        response = validate_and_save_subscriber(
            email="test@example.com",
            frequency="daily",
            name="Test User"
        )
        
        # Verify
        assert response.success is True
        assert response.message == "Subscription successful"
        assert response.subscriber_id is not None
        assert mock_save.called
    
    @patch('src.subscribe.subscription_logic.get_subscriber_by_email')
    def test_rejects_invalid_email(self, mock_get):
        """Should reject invalid email format"""
        response = validate_and_save_subscriber(
            email="invalid-email",
            frequency="daily"
        )
        
        assert response.success is False
        assert "Invalid email format" in response.message
        assert mock_get.called is False
    
    @patch('src.subscribe.subscription_logic.get_subscriber_by_email')
    def test_rejects_invalid_frequency(self, mock_get):
        """Should reject invalid frequency"""
        response = validate_and_save_subscriber(
            email="test@example.com",
            frequency="monthly"
        )
        
        assert response.success is False
        assert "Frequency must be" in response.message
        assert mock_get.called is False
    
    @patch('src.subscribe.subscription_logic.get_subscriber_by_email')
    @patch('src.subscribe.subscription_logic.save_subscriber_to_db')
    def test_rejects_duplicate_active_subscription(self, mock_save, mock_get):
        """Should reject when email already subscribed and active"""
        # Setup mock - existing active subscriber
        existing = Subscriber(
            subscriber_id="existing-id",
            email="test@example.com",
            name="Existing User",
            frequency="daily",
            subscribed_at=datetime.now(),
            active=True,
            unsubscribe_token="existing-token"
        )
        mock_get.return_value = existing
        
        # Execute
        response = validate_and_save_subscriber(
            email="test@example.com",
            frequency="daily"
        )
        
        # Verify
        assert response.success is False
        assert response.message == "Email already subscribed"
        assert mock_save.called is False
    
    @patch('src.subscribe.subscription_logic.get_subscriber_by_email')
    @patch('src.subscribe.subscription_logic.save_subscriber_to_db')
    def test_reactivates_inactive_subscription(self, mock_save, mock_get):
        """Should reactivate when email exists but inactive"""
        # Setup mock - existing inactive subscriber
        existing = Subscriber(
            subscriber_id="existing-id",
            email="test@example.com",
            name="Existing User",
            frequency="daily",
            subscribed_at=datetime.now(),
            active=False,
            unsubscribe_token="existing-token"
        )
        mock_get.return_value = existing
        mock_save.return_value = True
        
        # Execute
        response = validate_and_save_subscriber(
            email="test@example.com",
            frequency="weekly",  # Different frequency
            name="Updated Name"
        )
        
        # Verify
        assert response.success is True
        assert response.message == "Subscription reactivated"
        assert response.subscriber_id == "existing-id"
        assert mock_save.called
        
        # Verify the subscriber was updated
        saved_subscriber = mock_save.call_args[0][0]
        assert saved_subscriber.active is True
        assert saved_subscriber.frequency == "weekly"
        assert saved_subscriber.name == "Updated Name"
    
    @patch('src.subscribe.subscription_logic.get_subscriber_by_email')
    @patch('src.subscribe.subscription_logic.save_subscriber_to_db')
    def test_handles_database_save_failure(self, mock_save, mock_get):
        """Should handle database save failures gracefully"""
        mock_get.return_value = None
        mock_save.return_value = False  # Save fails
        
        response = validate_and_save_subscriber(
            email="test@example.com",
            frequency="daily"
        )
        
        assert response.success is False
        assert "Failed to save subscription" in response.message
    
    @patch('src.subscribe.subscription_logic.get_subscriber_by_email')
    @patch('src.subscribe.subscription_logic.save_subscriber_to_db')
    def test_normalizes_email_and_frequency(self, mock_save, mock_get):
        """Should normalize email to lowercase and trim whitespace"""
        mock_get.return_value = None
        mock_save.return_value = True
        
        response = validate_and_save_subscriber(
            email="  TEST@EXAMPLE.COM  ",
            frequency="  DAILY  "
        )
        
        assert response.success is True
        
        # Verify normalized values were used
        saved_subscriber = mock_save.call_args[0][0]
        assert saved_subscriber.email == "test@example.com"
        assert saved_subscriber.frequency == "daily"
