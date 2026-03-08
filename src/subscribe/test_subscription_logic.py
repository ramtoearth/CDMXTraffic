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


class TestWelcomeEmailIntegration:
    """
    Test welcome email integration in subscription flow
    
    Requirements validated:
    - 2.1: Send welcome newsletter to new subscribers
    - 2.2: Send welcome newsletter on reactivation
    - 2.3: Mark welcome newsletter with type "welcome"
    - 2.4: Subscription persists despite email failure
    """
    
    @patch('src.subscribe.subscription_logic.boto3.client')
    @patch('src.subscribe.subscription_logic.get_subscriber_by_email')
    @patch('src.subscribe.subscription_logic.save_subscriber_to_db')
    @patch.dict('os.environ', {'SEND_EMAIL_FUNCTION_NAME': 'test-send-email-function'})
    def test_sends_welcome_email_for_new_subscriber(self, mock_save, mock_get, mock_boto_client):
        """
        Requirement 2.1: Should send welcome email when new subscriber is created
        """
        # Setup mocks
        mock_get.return_value = None  # New subscriber
        mock_save.return_value = True
        mock_lambda = MagicMock()
        mock_lambda.invoke.return_value = {'StatusCode': 202}
        mock_boto_client.return_value = mock_lambda
        
        # Execute
        response = validate_and_save_subscriber(
            email="newuser@example.com",
            frequency="daily",
            name="New User"
        )
        
        # Verify subscription succeeded
        assert response.success is True
        assert response.message == "Subscription successful"
        
        # Verify Lambda was invoked
        assert mock_lambda.invoke.called
        call_args = mock_lambda.invoke.call_args
        
        # Verify function name
        assert call_args[1]['FunctionName'] == 'test-send-email-function'
        
        # Verify invocation type is async (Event)
        assert call_args[1]['InvocationType'] == 'Event'
        
        # Verify payload contains welcome email data
        import json
        payload = json.loads(call_args[1]['Payload'])
        assert payload['to_email'] == 'newuser@example.com'
        assert payload['to_name'] == 'New User'
        assert payload['newsletter_type'] == 'welcome'
        assert 'subject' in payload
        assert 'html_body' in payload
        assert 'text_body' in payload
    
    @patch('src.subscribe.subscription_logic.boto3.client')
    @patch('src.subscribe.subscription_logic.get_subscriber_by_email')
    @patch('src.subscribe.subscription_logic.save_subscriber_to_db')
    @patch.dict('os.environ', {'SEND_EMAIL_FUNCTION_NAME': 'test-send-email-function'})
    def test_sends_welcome_email_on_reactivation(self, mock_save, mock_get, mock_boto_client):
        """
        Requirement 2.2: Should send welcome email when subscription is reactivated
        """
        # Setup mocks - existing inactive subscriber
        existing = Subscriber(
            subscriber_id="existing-id",
            email="reactivate@example.com",
            name="Reactivated User",
            frequency="daily",
            subscribed_at=datetime.now(),
            active=False,
            unsubscribe_token="existing-token"
        )
        mock_get.return_value = existing
        mock_save.return_value = True
        mock_lambda = MagicMock()
        mock_lambda.invoke.return_value = {'StatusCode': 202}
        mock_boto_client.return_value = mock_lambda
        
        # Execute
        response = validate_and_save_subscriber(
            email="reactivate@example.com",
            frequency="weekly",
            name="Reactivated User"
        )
        
        # Verify reactivation succeeded
        assert response.success is True
        assert response.message == "Subscription reactivated"
        
        # Verify Lambda was invoked for welcome email
        assert mock_lambda.invoke.called
        call_args = mock_lambda.invoke.call_args
        
        import json
        payload = json.loads(call_args[1]['Payload'])
        assert payload['to_email'] == 'reactivate@example.com'
        assert payload['newsletter_type'] == 'welcome'
    
    @patch('src.subscribe.subscription_logic.boto3.client')
    @patch('src.subscribe.subscription_logic.get_subscriber_by_email')
    @patch('src.subscribe.subscription_logic.save_subscriber_to_db')
    @patch.dict('os.environ', {'SEND_EMAIL_FUNCTION_NAME': 'test-send-email-function'})
    def test_welcome_email_marked_as_welcome_type(self, mock_save, mock_get, mock_boto_client):
        """
        Requirement 2.3: Welcome newsletter should be marked with type "welcome"
        """
        mock_get.return_value = None
        mock_save.return_value = True
        mock_lambda = MagicMock()
        mock_lambda.invoke.return_value = {'StatusCode': 202}
        mock_boto_client.return_value = mock_lambda
        
        # Execute
        validate_and_save_subscriber(
            email="test@example.com",
            frequency="daily"
        )
        
        # Verify newsletter_type is "welcome"
        import json
        payload = json.loads(mock_lambda.invoke.call_args[1]['Payload'])
        assert payload['newsletter_type'] == 'welcome'
    
    @patch('src.subscribe.subscription_logic.boto3.client')
    @patch('src.subscribe.subscription_logic.get_subscriber_by_email')
    @patch('src.subscribe.subscription_logic.save_subscriber_to_db')
    @patch.dict('os.environ', {'SEND_EMAIL_FUNCTION_NAME': 'test-send-email-function'})
    def test_subscription_persists_when_email_fails(self, mock_save, mock_get, mock_boto_client):
        """
        Requirement 2.4: Subscription should remain active even if welcome email fails
        """
        # Setup mocks
        mock_get.return_value = None
        mock_save.return_value = True
        
        # Mock Lambda invoke to raise an exception
        mock_lambda = MagicMock()
        mock_lambda.invoke.side_effect = Exception("Lambda invocation failed")
        mock_boto_client.return_value = mock_lambda
        
        # Execute - should not raise exception
        response = validate_and_save_subscriber(
            email="test@example.com",
            frequency="daily",
            name="Test User"
        )
        
        # Verify subscription still succeeded despite email failure
        assert response.success is True
        assert response.message == "Subscription successful"
        assert response.subscriber_id is not None
        
        # Verify subscriber was saved to database
        assert mock_save.called
    
    @patch('src.subscribe.subscription_logic.get_subscriber_by_email')
    @patch('src.subscribe.subscription_logic.save_subscriber_to_db')
    @patch.dict('os.environ', {})  # No SEND_EMAIL_FUNCTION_NAME set
    def test_handles_missing_email_function_config(self, mock_save, mock_get):
        """
        Should handle missing SEND_EMAIL_FUNCTION_NAME gracefully
        """
        mock_get.return_value = None
        mock_save.return_value = True
        
        # Execute - should not raise exception
        response = validate_and_save_subscriber(
            email="test@example.com",
            frequency="daily"
        )
        
        # Verify subscription succeeded even without email config
        assert response.success is True
        assert response.message == "Subscription successful"
    
    @patch('src.subscribe.subscription_logic.boto3.client')
    @patch('src.subscribe.subscription_logic.get_subscriber_by_email')
    @patch('src.subscribe.subscription_logic.save_subscriber_to_db')
    @patch.dict('os.environ', {
        'SEND_EMAIL_FUNCTION_NAME': 'test-send-email-function',
        'LANDING_PAGE_URL': 'https://example.com'
    })
    def test_welcome_email_includes_unsubscribe_link(self, mock_save, mock_get, mock_boto_client):
        """
        Welcome email should include unsubscribe link with token
        """
        mock_get.return_value = None
        mock_save.return_value = True
        mock_lambda = MagicMock()
        mock_lambda.invoke.return_value = {'StatusCode': 202}
        mock_boto_client.return_value = mock_lambda
        
        # Execute
        response = validate_and_save_subscriber(
            email="test@example.com",
            frequency="daily",
            name="Test User"
        )
        
        # Get the saved subscriber to check token
        saved_subscriber = mock_save.call_args[0][0]
        assert saved_subscriber.unsubscribe_token
        
        # Verify email payload includes unsubscribe link
        import json
        payload = json.loads(mock_lambda.invoke.call_args[1]['Payload'])
        
        # Check that HTML and text bodies contain unsubscribe link
        assert 'unsubscribe' in payload['html_body'].lower()
        assert 'unsubscribe' in payload['text_body'].lower()
        assert saved_subscriber.unsubscribe_token in payload['html_body']
        assert saved_subscriber.unsubscribe_token in payload['text_body']
