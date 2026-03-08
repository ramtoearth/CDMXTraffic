"""
Unit tests for Send Email Lambda handler

Tests the lambda_handler function that processes EmailRequest events
"""
import pytest
import json
import os
import sys
from unittest.mock import Mock, patch

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from send_email.handler import lambda_handler
from shared.models import EmailResponse


class TestSendEmailHandler:
    """Test suite for Send Email Lambda handler"""
    
    @patch('send_email.handler.send_email_via_zavu')
    def test_handler_success(self, mock_send_email):
        """Test successful email send through handler"""
        # Mock successful email send
        mock_send_email.return_value = EmailResponse(
            success=True,
            message_id='msg-123'
        )
        
        # Create event
        event = {
            'to_email': 'test@example.com',
            'to_name': 'Test User',
            'subject': 'Test Newsletter',
            'html_body': '<p>Test HTML content</p>',
            'text_body': 'Test text content',
            'newsletter_type': 'welcome'
        }
        
        # Call handler
        result = lambda_handler(event, None)
        
        # Verify
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['success'] is True
        assert body['message_id'] == 'msg-123'
        
        # Verify send_email_via_zavu was called with correct params
        mock_send_email.assert_called_once_with(
            to_email='test@example.com',
            subject='Test Newsletter',
            html_body='<p>Test HTML content</p>',
            text_body='Test text content',
            to_name='Test User'
        )
    
    @patch('send_email.handler.send_email_via_zavu')
    def test_handler_email_failure(self, mock_send_email):
        """Test handler when email send fails"""
        # Mock failed email send
        mock_send_email.return_value = EmailResponse(
            success=False,
            error='Zavu API error'
        )
        
        # Create event
        event = {
            'to_email': 'test@example.com',
            'subject': 'Test Newsletter',
            'html_body': '<p>Test HTML</p>',
            'text_body': 'Test text',
            'newsletter_type': 'daily'
        }
        
        # Call handler
        result = lambda_handler(event, None)
        
        # Verify
        assert result['statusCode'] == 500
        body = json.loads(result['body'])
        assert body['success'] is False
        assert 'error' in body
    
    def test_handler_missing_to_email(self):
        """Test handler with missing to_email field"""
        # Create event without to_email
        event = {
            'subject': 'Test Newsletter',
            'html_body': '<p>Test HTML</p>',
            'text_body': 'Test text'
        }
        
        # Call handler
        result = lambda_handler(event, None)
        
        # Verify
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert body['success'] is False
        assert 'to_email' in body['error']
    
    def test_handler_missing_subject(self):
        """Test handler with missing subject field"""
        # Create event without subject
        event = {
            'to_email': 'test@example.com',
            'html_body': '<p>Test HTML</p>',
            'text_body': 'Test text'
        }
        
        # Call handler
        result = lambda_handler(event, None)
        
        # Verify
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert body['success'] is False
        assert 'subject' in body['error']
    
    def test_handler_missing_html_body(self):
        """Test handler with missing html_body field"""
        # Create event without html_body
        event = {
            'to_email': 'test@example.com',
            'subject': 'Test Newsletter',
            'text_body': 'Test text'
        }
        
        # Call handler
        result = lambda_handler(event, None)
        
        # Verify
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert body['success'] is False
        assert 'html_body' in body['error']
    
    def test_handler_missing_text_body(self):
        """Test handler with missing text_body field"""
        # Create event without text_body
        event = {
            'to_email': 'test@example.com',
            'subject': 'Test Newsletter',
            'html_body': '<p>Test HTML</p>'
        }
        
        # Call handler
        result = lambda_handler(event, None)
        
        # Verify
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert body['success'] is False
        assert 'text_body' in body['error']
    
    @patch('send_email.handler.send_email_via_zavu')
    def test_handler_includes_both_html_and_text(self, mock_send_email):
        """Test that handler includes both HTML and text body in email (Requirement 6.2)"""
        # Mock successful email send
        mock_send_email.return_value = EmailResponse(
            success=True,
            message_id='msg-456'
        )
        
        # Create event with both formats
        html_content = '<html><body><h1>Newsletter</h1><p>Content here</p></body></html>'
        text_content = 'Newsletter\n\nContent here'
        
        event = {
            'to_email': 'subscriber@example.com',
            'subject': 'Daily Traffic Update',
            'html_body': html_content,
            'text_body': text_content,
            'newsletter_type': 'daily'
        }
        
        # Call handler
        result = lambda_handler(event, None)
        
        # Verify both formats were passed to send function
        mock_send_email.assert_called_once()
        call_kwargs = mock_send_email.call_args[1]
        assert call_kwargs['html_body'] == html_content
        assert call_kwargs['text_body'] == text_content
        
        # Verify success
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['success'] is True
    
    @patch('send_email.handler.send_email_via_zavu')
    def test_handler_logs_success(self, mock_send_email, caplog):
        """Test that handler logs successful email sends (Requirement 6.5, 10.3)"""
        # Mock successful email send
        mock_send_email.return_value = EmailResponse(
            success=True,
            message_id='msg-789'
        )
        
        # Create event
        event = {
            'to_email': 'test@example.com',
            'subject': 'Test',
            'html_body': '<p>Test</p>',
            'text_body': 'Test',
            'newsletter_type': 'welcome'
        }
        
        # Call handler
        with caplog.at_level('INFO'):
            result = lambda_handler(event, None)
        
        # Verify logging occurred
        assert 'Email sent successfully' in caplog.text
        assert 'test@example.com' in caplog.text
        assert 'msg-789' in caplog.text
    
    @patch('send_email.handler.send_email_via_zavu')
    def test_handler_logs_failure(self, mock_send_email, caplog):
        """Test that handler logs failed email sends (Requirement 6.5, 10.3)"""
        # Mock failed email send
        mock_send_email.return_value = EmailResponse(
            success=False,
            error='API connection timeout'
        )
        
        # Create event
        event = {
            'to_email': 'test@example.com',
            'subject': 'Test',
            'html_body': '<p>Test</p>',
            'text_body': 'Test'
        }
        
        # Call handler
        with caplog.at_level('ERROR'):
            result = lambda_handler(event, None)
        
        # Verify error logging occurred
        assert 'Failed to send email' in caplog.text
        assert 'test@example.com' in caplog.text
        assert 'API connection timeout' in caplog.text
    
    @patch('send_email.handler.send_email_via_zavu')
    def test_handler_default_newsletter_type(self, mock_send_email):
        """Test that handler defaults newsletter_type to 'daily' if not provided"""
        # Mock successful email send
        mock_send_email.return_value = EmailResponse(
            success=True,
            message_id='msg-default'
        )
        
        # Create event without newsletter_type
        event = {
            'to_email': 'test@example.com',
            'subject': 'Test',
            'html_body': '<p>Test</p>',
            'text_body': 'Test'
        }
        
        # Call handler
        result = lambda_handler(event, None)
        
        # Verify success
        assert result['statusCode'] == 200


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
