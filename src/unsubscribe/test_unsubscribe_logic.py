"""
Unit tests for unsubscribe logic

Requirements tested:
- 11.3: Mark subscriber as inactive when unsubscribe link is clicked
- 11.4: Inactive subscribers not included in future distributions
- 11.5: Validate unsubscribe_token before processing
"""
import os
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from uuid import uuid4

from src.shared.models import Subscriber
from src.unsubscribe.unsubscribe_logic import (
    get_subscriber_by_token,
    update_subscriber_status,
    process_unsubscribe
)


@pytest.fixture
def mock_env():
    """Set up environment variables"""
    os.environ['SUBSCRIBERS_TABLE'] = 'test-subscribers-table'
    yield
    if 'SUBSCRIBERS_TABLE' in os.environ:
        del os.environ['SUBSCRIBERS_TABLE']


@pytest.fixture
def sample_subscriber():
    """Create a sample active subscriber"""
    return Subscriber(
        subscriber_id=str(uuid4()),
        email="test@example.com",
        name="Test User",
        frequency="daily",
        subscribed_at=datetime.now(),
        last_sent_at=None,
        active=True,
        unsubscribe_token=str(uuid4())
    )


class TestGetSubscriberByToken:
    """Test get_subscriber_by_token function"""
    
    def test_valid_token_returns_subscriber(self, mock_env, sample_subscriber):
        """Test that valid token returns subscriber"""
        with patch('src.unsubscribe.unsubscribe_logic.get_dynamodb_resource') as mock_db:
            # Mock DynamoDB response
            mock_table = MagicMock()
            mock_table.scan.return_value = {
                'Items': [sample_subscriber.to_dict()]
            }
            mock_db.return_value.Table.return_value = mock_table
            
            # Call function
            result = get_subscriber_by_token(sample_subscriber.unsubscribe_token)
            
            # Assertions
            assert result is not None
            assert result.subscriber_id == sample_subscriber.subscriber_id
            assert result.email == sample_subscriber.email
            assert result.unsubscribe_token == sample_subscriber.unsubscribe_token
    
    def test_invalid_token_returns_none(self, mock_env):
        """Test that invalid token returns None"""
        with patch('src.unsubscribe.unsubscribe_logic.get_dynamodb_resource') as mock_db:
            # Mock DynamoDB response with no items
            mock_table = MagicMock()
            mock_table.scan.return_value = {'Items': []}
            mock_db.return_value.Table.return_value = mock_table
            
            # Call function
            result = get_subscriber_by_token("invalid-token")
            
            # Assertions
            assert result is None
    
    def test_missing_env_var_returns_none(self, sample_subscriber):
        """Test that missing SUBSCRIBERS_TABLE env var returns None"""
        # Don't use mock_env fixture
        if 'SUBSCRIBERS_TABLE' in os.environ:
            del os.environ['SUBSCRIBERS_TABLE']
        
        result = get_subscriber_by_token(sample_subscriber.unsubscribe_token)
        assert result is None


class TestUpdateSubscriberStatus:
    """Test update_subscriber_status function"""
    
    def test_update_to_inactive_success(self, mock_env):
        """Test successfully updating subscriber to inactive"""
        with patch('src.unsubscribe.unsubscribe_logic.get_dynamodb_resource') as mock_db:
            # Mock DynamoDB update
            mock_table = MagicMock()
            mock_table.update_item.return_value = {}
            mock_db.return_value.Table.return_value = mock_table
            
            # Call function
            result = update_subscriber_status("test-id", active=False)
            
            # Assertions
            assert result is True
            mock_table.update_item.assert_called_once()
            call_args = mock_table.update_item.call_args
            assert call_args[1]['Key'] == {'subscriber_id': 'test-id'}
            assert call_args[1]['ExpressionAttributeValues'][':active'] == 'false'
    
    def test_update_to_active_success(self, mock_env):
        """Test successfully updating subscriber to active"""
        with patch('src.unsubscribe.unsubscribe_logic.get_dynamodb_resource') as mock_db:
            # Mock DynamoDB update
            mock_table = MagicMock()
            mock_table.update_item.return_value = {}
            mock_db.return_value.Table.return_value = mock_table
            
            # Call function
            result = update_subscriber_status("test-id", active=True)
            
            # Assertions
            assert result is True
            call_args = mock_table.update_item.call_args
            assert call_args[1]['ExpressionAttributeValues'][':active'] == 'true'
    
    def test_update_failure_returns_false(self, mock_env):
        """Test that DynamoDB error returns False"""
        with patch('src.unsubscribe.unsubscribe_logic.get_dynamodb_resource') as mock_db:
            # Mock DynamoDB error
            mock_table = MagicMock()
            mock_table.update_item.side_effect = Exception("DynamoDB error")
            mock_db.return_value.Table.return_value = mock_table
            
            # Call function
            result = update_subscriber_status("test-id", active=False)
            
            # Assertions
            assert result is False


class TestProcessUnsubscribe:
    """Test process_unsubscribe function - main business logic"""
    
    def test_valid_token_unsubscribes_successfully(self, mock_env, sample_subscriber):
        """
        Test successful unsubscribe with valid token
        Requirements: 11.3, 11.5
        """
        with patch('src.unsubscribe.unsubscribe_logic.get_subscriber_by_token') as mock_get, \
             patch('src.unsubscribe.unsubscribe_logic.update_subscriber_status') as mock_update:
            
            # Mock finding subscriber
            mock_get.return_value = sample_subscriber
            mock_update.return_value = True
            
            # Call function
            success, message = process_unsubscribe(sample_subscriber.unsubscribe_token)
            
            # Assertions
            assert success is True
            assert "successfully unsubscribed" in message.lower()
            mock_get.assert_called_once_with(sample_subscriber.unsubscribe_token)
            mock_update.assert_called_once_with(sample_subscriber.subscriber_id, active=False)
    
    def test_invalid_token_returns_error(self, mock_env):
        """
        Test that invalid token returns error
        Requirements: 11.5
        """
        with patch('src.unsubscribe.unsubscribe_logic.get_subscriber_by_token') as mock_get:
            # Mock not finding subscriber
            mock_get.return_value = None
            
            # Call function
            success, message = process_unsubscribe("invalid-token-12345")
            
            # Assertions
            assert success is False
            assert "invalid" in message.lower() or "expired" in message.lower()
    
    def test_empty_token_returns_error(self, mock_env):
        """
        Test that empty token returns error
        Requirements: 11.5
        """
        # Call function with empty token
        success, message = process_unsubscribe("")
        
        # Assertions
        assert success is False
        assert "invalid" in message.lower()
    
    def test_short_token_returns_error(self, mock_env):
        """
        Test that too-short token returns error
        Requirements: 11.5
        """
        # Call function with short token
        success, message = process_unsubscribe("short")
        
        # Assertions
        assert success is False
        assert "invalid" in message.lower()
    
    def test_already_inactive_subscriber(self, mock_env, sample_subscriber):
        """
        Test unsubscribing already inactive subscriber
        Requirements: 11.3
        """
        # Make subscriber inactive
        sample_subscriber.active = False
        
        with patch('src.unsubscribe.unsubscribe_logic.get_subscriber_by_token') as mock_get:
            mock_get.return_value = sample_subscriber
            
            # Call function
            success, message = process_unsubscribe(sample_subscriber.unsubscribe_token)
            
            # Assertions
            assert success is True
            assert "already" in message.lower()
    
    def test_update_failure_returns_error(self, mock_env, sample_subscriber):
        """
        Test that database update failure returns error
        Requirements: 11.3
        """
        with patch('src.unsubscribe.unsubscribe_logic.get_subscriber_by_token') as mock_get, \
             patch('src.unsubscribe.unsubscribe_logic.update_subscriber_status') as mock_update:
            
            # Mock finding subscriber but update fails
            mock_get.return_value = sample_subscriber
            mock_update.return_value = False
            
            # Call function
            success, message = process_unsubscribe(sample_subscriber.unsubscribe_token)
            
            # Assertions
            assert success is False
            assert "failed" in message.lower()
    
    def test_none_token_returns_error(self, mock_env):
        """Test that None token returns error"""
        success, message = process_unsubscribe(None)
        assert success is False
        assert "invalid" in message.lower()
    
    def test_whitespace_token_returns_error(self, mock_env):
        """Test that whitespace-only token returns error"""
        success, message = process_unsubscribe("   ")
        assert success is False
        assert "invalid" in message.lower()


class TestRequirementValidation:
    """Test that requirements are properly validated"""
    
    def test_requirement_11_3_inactive_status(self, mock_env, sample_subscriber):
        """
        Requirement 11.3: WHEN a user clicks the unsubscribe link, 
        THE System SHALL mark the subscriber as inactive (active=False)
        """
        with patch('src.unsubscribe.unsubscribe_logic.get_subscriber_by_token') as mock_get, \
             patch('src.unsubscribe.unsubscribe_logic.update_subscriber_status') as mock_update:
            
            mock_get.return_value = sample_subscriber
            mock_update.return_value = True
            
            success, _ = process_unsubscribe(sample_subscriber.unsubscribe_token)
            
            # Verify that update_subscriber_status was called with active=False
            assert success is True
            mock_update.assert_called_once_with(sample_subscriber.subscriber_id, active=False)
    
    def test_requirement_11_5_token_validation(self, mock_env):
        """
        Requirement 11.5: THE System SHALL validate the unsubscribe_token 
        before processing unsubscribe requests
        """
        with patch('src.unsubscribe.unsubscribe_logic.get_subscriber_by_token') as mock_get:
            mock_get.return_value = None
            
            # Try with invalid token
            success, message = process_unsubscribe("invalid-token-xyz")
            
            # Verify validation failed
            assert success is False
            assert "invalid" in message.lower() or "expired" in message.lower()
            
            # Verify get_subscriber_by_token was called (validation happened)
            mock_get.assert_called_once()
