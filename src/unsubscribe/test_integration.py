"""
Integration tests for unsubscribe functionality

These tests verify the complete unsubscribe flow including:
- Token validation
- Database updates
- Handler response formatting

Requirements tested:
- 11.3: Mark subscriber as inactive when unsubscribe link is clicked
- 11.4: Inactive subscribers not included in future distributions
- 11.5: Validate unsubscribe_token before processing
"""
import json
import os
import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import patch, MagicMock

from src.shared.models import Subscriber
from src.unsubscribe.handler import lambda_handler


@pytest.fixture
def mock_env():
    """Set up environment variables"""
    os.environ['SUBSCRIBERS_TABLE'] = 'test-subscribers-table'
    yield
    if 'SUBSCRIBERS_TABLE' in os.environ:
        del os.environ['SUBSCRIBERS_TABLE']


@pytest.fixture
def active_subscriber():
    """Create an active subscriber"""
    return Subscriber(
        subscriber_id=str(uuid4()),
        email="active@example.com",
        name="Active User",
        frequency="daily",
        subscribed_at=datetime.now(),
        last_sent_at=None,
        active=True,
        unsubscribe_token=str(uuid4())
    )


@pytest.fixture
def inactive_subscriber():
    """Create an inactive subscriber"""
    return Subscriber(
        subscriber_id=str(uuid4()),
        email="inactive@example.com",
        name="Inactive User",
        frequency="daily",
        subscribed_at=datetime.now(),
        last_sent_at=None,
        active=False,
        unsubscribe_token=str(uuid4())
    )


class TestUnsubscribeIntegration:
    """Integration tests for complete unsubscribe flow"""
    
    def test_complete_unsubscribe_flow(self, mock_env, active_subscriber):
        """
        Test complete flow: valid token -> find subscriber -> update status -> return success
        Requirements: 11.3, 11.5
        """
        event = {
            'body': json.dumps({
                'token': active_subscriber.unsubscribe_token
            })
        }
        
        with patch('src.unsubscribe.unsubscribe_logic.get_dynamodb_resource') as mock_db:
            # Mock DynamoDB scan to find subscriber
            mock_table = MagicMock()
            mock_table.scan.return_value = {
                'Items': [active_subscriber.to_dict()]
            }
            mock_table.update_item.return_value = {}
            mock_db.return_value.Table.return_value = mock_table
            
            # Execute handler
            response = lambda_handler(event, None)
            
            # Verify response
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['success'] is True
            assert 'successfully unsubscribed' in body['message'].lower()
            
            # Verify DynamoDB was called correctly
            mock_table.scan.assert_called_once()
            mock_table.update_item.assert_called_once()
            
            # Verify update_item was called with correct parameters
            update_call = mock_table.update_item.call_args
            assert update_call[1]['Key']['subscriber_id'] == active_subscriber.subscriber_id
            assert update_call[1]['ExpressionAttributeValues'][':active'] == 'false'
    
    def test_unsubscribe_already_inactive(self, mock_env, inactive_subscriber):
        """
        Test unsubscribing already inactive subscriber
        Requirements: 11.3
        """
        event = {
            'body': json.dumps({
                'token': inactive_subscriber.unsubscribe_token
            })
        }
        
        with patch('src.unsubscribe.unsubscribe_logic.get_dynamodb_resource') as mock_db:
            # Mock DynamoDB scan to find inactive subscriber
            mock_table = MagicMock()
            mock_table.scan.return_value = {
                'Items': [inactive_subscriber.to_dict()]
            }
            mock_db.return_value.Table.return_value = mock_table
            
            # Execute handler
            response = lambda_handler(event, None)
            
            # Verify response
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['success'] is True
            assert 'already' in body['message'].lower()
            
            # Verify update_item was NOT called (already inactive)
            mock_table.update_item.assert_not_called()
    
    def test_invalid_token_flow(self, mock_env):
        """
        Test complete flow with invalid token
        Requirements: 11.5
        """
        event = {
            'body': json.dumps({
                'token': 'invalid-token-xyz'
            })
        }
        
        with patch('src.unsubscribe.unsubscribe_logic.get_dynamodb_resource') as mock_db:
            # Mock DynamoDB scan returning no results
            mock_table = MagicMock()
            mock_table.scan.return_value = {'Items': []}
            mock_db.return_value.Table.return_value = mock_table
            
            # Execute handler
            response = lambda_handler(event, None)
            
            # Verify response
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert body['success'] is False
            assert 'invalid' in body['message'].lower() or 'expired' in body['message'].lower()
            
            # Verify update_item was NOT called
            mock_table.update_item.assert_not_called()
    
    def test_database_error_handling(self, mock_env, active_subscriber):
        """
        Test handling of database errors during update
        Requirements: 11.3
        """
        event = {
            'body': json.dumps({
                'token': active_subscriber.unsubscribe_token
            })
        }
        
        with patch('src.unsubscribe.unsubscribe_logic.get_dynamodb_resource') as mock_db:
            # Mock DynamoDB scan succeeds but update fails
            mock_table = MagicMock()
            mock_table.scan.return_value = {
                'Items': [active_subscriber.to_dict()]
            }
            mock_table.update_item.side_effect = Exception("Database error")
            mock_db.return_value.Table.return_value = mock_table
            
            # Execute handler
            response = lambda_handler(event, None)
            
            # Verify response
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert body['success'] is False
            assert 'failed' in body['message'].lower()
    
    def test_requirement_11_4_inactive_excluded(self, mock_env, active_subscriber):
        """
        Requirement 11.4: WHEN a subscriber is marked inactive, 
        THE System SHALL not include them in future newsletter distributions
        
        This test verifies that after unsubscribe, the active field is set to 'false',
        which will cause the subscriber to be excluded from queries using the
        frequency-active-index GSI.
        """
        event = {
            'body': json.dumps({
                'token': active_subscriber.unsubscribe_token
            })
        }
        
        with patch('src.unsubscribe.unsubscribe_logic.get_dynamodb_resource') as mock_db:
            mock_table = MagicMock()
            mock_table.scan.return_value = {
                'Items': [active_subscriber.to_dict()]
            }
            mock_table.update_item.return_value = {}
            mock_db.return_value.Table.return_value = mock_table
            
            # Execute handler
            response = lambda_handler(event, None)
            
            # Verify success
            assert response['statusCode'] == 200
            
            # Verify that active was set to 'false' (string, as stored in DynamoDB)
            update_call = mock_table.update_item.call_args
            assert update_call[1]['ExpressionAttributeValues'][':active'] == 'false'
            
            # This 'false' value will cause the subscriber to be excluded from
            # queries like: frequency = 'daily' AND active = 'true'


class TestRateLimitingConfiguration:
    """Test that rate limiting is properly configured"""
    
    def test_rate_limiting_documented(self):
        """
        Verify that rate limiting is configured in template.yaml
        Requirements: 11.5 (rate limiting for unsubscribe endpoint)
        """
        # Read template.yaml to verify rate limiting configuration
        with open('template.yaml', 'r') as f:
            template_content = f.read()
        
        # Verify rate limiting is mentioned
        assert 'ThrottlingRateLimit' in template_content or 'RateLimit' in template_content
        
        # Verify unsubscribe endpoint is mentioned
        assert '/unsubscribe' in template_content
