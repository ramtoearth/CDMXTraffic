"""
Tests for Subscribe Lambda Handler

Verifies Task 2.5 requirements:
- Lambda handler properly parses JSON request body
- Returns appropriate HTTP status codes (200, 400, 500)
- Includes CORS headers
- Comprehensive error handling
"""
import json
import pytest
from unittest.mock import patch, MagicMock

from src.subscribe.handler import lambda_handler
from src.shared.models import SubscribeResponse


class TestLambdaHandler:
    """Test suite for lambda_handler function"""
    
    def test_successful_subscription_with_json_string_body(self):
        """Test successful subscription with JSON string in body"""
        event = {
            'body': json.dumps({
                'email': 'test@example.com',
                'frequency': 'daily',
                'name': 'Test User'
            })
        }
        
        mock_response = SubscribeResponse(
            success=True,
            message='Subscription successful',
            subscriber_id='test-uuid-123'
        )
        
        with patch('src.subscribe.handler.validate_and_save_subscriber', return_value=mock_response):
            response = lambda_handler(event, None)
        
        # Verify HTTP status code
        assert response['statusCode'] == 200
        
        # Verify CORS headers
        assert 'Access-Control-Allow-Origin' in response['headers']
        assert response['headers']['Access-Control-Allow-Origin'] == '*'
        assert response['headers']['Content-Type'] == 'application/json'
        
        # Verify response body
        body = json.loads(response['body'])
        assert body['success'] is True
        assert body['message'] == 'Subscription successful'
        assert body['subscriber_id'] == 'test-uuid-123'
    
    def test_successful_subscription_with_dict_body(self):
        """Test successful subscription with dict in body (API Gateway proxy)"""
        event = {
            'body': {
                'email': 'test@example.com',
                'frequency': 'weekly',
                'name': 'Test User'
            }
        }
        
        mock_response = SubscribeResponse(
            success=True,
            message='Subscription successful',
            subscriber_id='test-uuid-456'
        )
        
        with patch('src.subscribe.handler.validate_and_save_subscriber', return_value=mock_response):
            response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True
    
    def test_invalid_email_returns_400(self):
        """Test that invalid email returns 400 status code"""
        event = {
            'body': json.dumps({
                'email': 'invalid-email',
                'frequency': 'daily'
            })
        }
        
        mock_response = SubscribeResponse(
            success=False,
            message='Invalid email format'
        )
        
        with patch('src.subscribe.handler.validate_and_save_subscriber', return_value=mock_response):
            response = lambda_handler(event, None)
        
        # Verify 400 status code for validation error
        assert response['statusCode'] == 400
        
        # Verify CORS headers still present
        assert 'Access-Control-Allow-Origin' in response['headers']
        
        # Verify error message
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'Invalid email format' in body['message']
    
    def test_duplicate_email_returns_400(self):
        """Test that duplicate email returns 400 status code"""
        event = {
            'body': json.dumps({
                'email': 'existing@example.com',
                'frequency': 'daily'
            })
        }
        
        mock_response = SubscribeResponse(
            success=False,
            message='Email already subscribed'
        )
        
        with patch('src.subscribe.handler.validate_and_save_subscriber', return_value=mock_response):
            response = lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'Email already subscribed' in body['message']
    
    def test_invalid_json_returns_400(self):
        """Test that invalid JSON in body returns 400 status code"""
        event = {
            'body': 'invalid json {'
        }
        
        response = lambda_handler(event, None)
        
        # Verify 400 status code for JSON parse error
        assert response['statusCode'] == 400
        
        # Verify CORS headers
        assert 'Access-Control-Allow-Origin' in response['headers']
        
        # Verify error message
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'Invalid JSON' in body['message']
    
    def test_unexpected_exception_returns_500(self):
        """Test that unexpected exceptions return 500 status code"""
        event = {
            'body': json.dumps({
                'email': 'test@example.com',
                'frequency': 'daily'
            })
        }
        
        # Mock validate_and_save_subscriber to raise an exception
        with patch('src.subscribe.handler.validate_and_save_subscriber', side_effect=Exception('Database error')):
            response = lambda_handler(event, None)
        
        # Verify 500 status code for internal error
        assert response['statusCode'] == 500
        
        # Verify CORS headers
        assert 'Access-Control-Allow-Origin' in response['headers']
        
        # Verify error message
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'Internal server error' in body['message']
    
    def test_missing_body_returns_400(self):
        """Test that missing body returns 400 status code"""
        event = {}
        
        mock_response = SubscribeResponse(
            success=False,
            message='Invalid email format'
        )
        
        with patch('src.subscribe.handler.validate_and_save_subscriber', return_value=mock_response):
            response = lambda_handler(event, None)
        
        # Should handle gracefully and return 400
        assert response['statusCode'] == 400
    
    def test_cors_headers_always_present(self):
        """Test that CORS headers are present in all responses"""
        test_cases = [
            # Success case
            {
                'body': json.dumps({'email': 'test@example.com', 'frequency': 'daily'}),
                'mock_response': SubscribeResponse(True, 'Success', 'id-123')
            },
            # Validation error
            {
                'body': json.dumps({'email': 'invalid', 'frequency': 'daily'}),
                'mock_response': SubscribeResponse(False, 'Invalid email')
            },
            # Invalid JSON
            {
                'body': 'invalid json',
                'mock_response': None  # Won't be used
            }
        ]
        
        for test_case in test_cases:
            event = {'body': test_case['body']}
            
            if test_case['mock_response']:
                with patch('src.subscribe.handler.validate_and_save_subscriber', 
                          return_value=test_case['mock_response']):
                    response = lambda_handler(event, None)
            else:
                response = lambda_handler(event, None)
            
            # Verify CORS headers always present
            assert 'Access-Control-Allow-Origin' in response['headers']
            assert response['headers']['Access-Control-Allow-Origin'] == '*'
            assert 'Content-Type' in response['headers']
            assert response['headers']['Content-Type'] == 'application/json'
    
    def test_response_body_always_json(self):
        """Test that response body is always valid JSON"""
        event = {
            'body': json.dumps({
                'email': 'test@example.com',
                'frequency': 'daily'
            })
        }
        
        mock_response = SubscribeResponse(
            success=True,
            message='Subscription successful',
            subscriber_id='test-id'
        )
        
        with patch('src.subscribe.handler.validate_and_save_subscriber', return_value=mock_response):
            response = lambda_handler(event, None)
        
        # Verify body is valid JSON
        body = json.loads(response['body'])
        assert isinstance(body, dict)
        assert 'success' in body
        assert 'message' in body
