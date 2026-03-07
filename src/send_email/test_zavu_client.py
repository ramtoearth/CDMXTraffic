"""
Unit tests for Zavu API client

Tests basic functionality without making actual API calls
"""
import pytest
import json
import os
import sys
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from send_email.zavu_client import send_email_via_zavu, get_zavu_api_key
from shared.models import EmailResponse


class TestZavuClient:
    """Test suite for Zavu API client"""
    
    @patch('send_email.zavu_client.boto3.session.Session')
    def test_get_zavu_api_key_success(self, mock_session):
        """Test successful API key retrieval from Secrets Manager"""
        # Mock Secrets Manager response
        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {
            'SecretString': json.dumps({'api_key': 'test-api-key-123'})
        }
        mock_session.return_value.client.return_value = mock_client
        
        # Set environment variable
        os.environ['ZAVU_API_KEY_SECRET'] = 'test-secret-name'
        
        # Call function
        api_key = get_zavu_api_key()
        
        # Verify
        assert api_key == 'test-api-key-123'
        mock_client.get_secret_value.assert_called_once()
    
    def test_get_zavu_api_key_missing_env_var(self):
        """Test error when ZAVU_API_KEY_SECRET is not set"""
        # Remove environment variable if it exists
        if 'ZAVU_API_KEY_SECRET' in os.environ:
            del os.environ['ZAVU_API_KEY_SECRET']
        
        # Should raise exception
        with pytest.raises(Exception, match="ZAVU_API_KEY_SECRET environment variable not set"):
            get_zavu_api_key()
    
    @patch('send_email.zavu_client.requests.post')
    @patch('send_email.zavu_client.get_zavu_api_key')
    def test_send_email_success(self, mock_get_key, mock_post):
        """Test successful email send"""
        # Mock API key retrieval
        mock_get_key.return_value = 'test-api-key'
        
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'message_id': 'msg-123'}
        mock_post.return_value = mock_response
        
        # Call function
        result = send_email_via_zavu(
            to_email='test@example.com',
            subject='Test Subject',
            html_body='<p>Test HTML</p>',
            text_body='Test Text'
        )
        
        # Verify
        assert result.success is True
        assert result.message_id == 'msg-123'
        assert result.error is None
        mock_post.assert_called_once()
    
    @patch('send_email.zavu_client.requests.post')
    @patch('send_email.zavu_client.get_zavu_api_key')
    def test_send_email_rate_limit_retry(self, mock_get_key, mock_post):
        """Test retry logic on rate limit (429)"""
        # Mock API key retrieval
        mock_get_key.return_value = 'test-api-key'
        
        # Mock rate limit response followed by success
        mock_rate_limit = Mock()
        mock_rate_limit.status_code = 429
        mock_rate_limit.headers = {'Retry-After': '1'}
        
        mock_success = Mock()
        mock_success.status_code = 200
        mock_success.json.return_value = {'message_id': 'msg-456'}
        
        mock_post.side_effect = [mock_rate_limit, mock_success]
        
        # Call function
        result = send_email_via_zavu(
            to_email='test@example.com',
            subject='Test Subject',
            html_body='<p>Test HTML</p>',
            text_body='Test Text'
        )
        
        # Verify - should succeed after retry
        assert result.success is True
        assert result.message_id == 'msg-456'
        assert mock_post.call_count == 2
    
    @patch('send_email.zavu_client.requests.post')
    @patch('send_email.zavu_client.get_zavu_api_key')
    def test_send_email_max_retries_exceeded(self, mock_get_key, mock_post):
        """Test failure after max retries"""
        # Mock API key retrieval
        mock_get_key.return_value = 'test-api-key'
        
        # Mock rate limit response for all attempts
        mock_rate_limit = Mock()
        mock_rate_limit.status_code = 429
        mock_rate_limit.headers = {'Retry-After': '0'}
        mock_post.return_value = mock_rate_limit
        
        # Call function
        result = send_email_via_zavu(
            to_email='test@example.com',
            subject='Test Subject',
            html_body='<p>Test HTML</p>',
            text_body='Test Text'
        )
        
        # Verify - should fail after 3 attempts
        assert result.success is False
        assert result.error is not None
        assert 'Rate limited' in result.error
        assert mock_post.call_count == 3
    
    @patch('send_email.zavu_client.get_zavu_api_key')
    def test_send_email_api_key_failure(self, mock_get_key):
        """Test handling of API key retrieval failure"""
        # Mock API key retrieval failure
        mock_get_key.side_effect = Exception("Failed to get API key")
        
        # Call function
        result = send_email_via_zavu(
            to_email='test@example.com',
            subject='Test Subject',
            html_body='<p>Test HTML</p>',
            text_body='Test Text'
        )
        
        # Verify
        assert result.success is False
        assert 'Failed to retrieve API key' in result.error
    
    @patch('send_email.zavu_client.requests.post')
    @patch('send_email.zavu_client.get_zavu_api_key')
    def test_send_email_includes_both_formats(self, mock_get_key, mock_post):
        """Test that both HTML and text formats are included in request"""
        # Mock API key retrieval
        mock_get_key.return_value = 'test-api-key'
        
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'message_id': 'msg-789'}
        mock_post.return_value = mock_response
        
        # Call function
        html_content = '<p>HTML content</p>'
        text_content = 'Text content'
        
        result = send_email_via_zavu(
            to_email='test@example.com',
            subject='Test Subject',
            html_body=html_content,
            text_body=text_content
        )
        
        # Verify both formats are in the request
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        
        assert payload['html'] == html_content
        assert payload['text'] == text_content
        assert result.success is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
