"""
Unit tests for unsubscribe Lambda handler

Requirements tested:
- 11.3: Mark subscriber as inactive when unsubscribe link is clicked
- 11.5: Validate unsubscribe_token before processing
"""
import json
import pytest
from unittest.mock import patch

from src.unsubscribe.handler import lambda_handler


class TestLambdaHandler:
    """Test Lambda handler function"""
    
    def test_successful_unsubscribe(self):
        """Test successful unsubscribe request"""
        event = {
            'body': json.dumps({
                'token': 'valid-token-12345678'
            })
        }
        
        with patch('src.unsubscribe.handler.process_unsubscribe') as mock_process:
            mock_process.return_value = (True, "You have been successfully unsubscribed")
            
            response = lambda_handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['success'] is True
            assert 'unsubscribed' in body['message'].lower()
    
    def test_invalid_token(self):
        """Test unsubscribe with invalid token"""
        event = {
            'body': json.dumps({
                'token': 'invalid-token'
            })
        }
        
        with patch('src.unsubscribe.handler.process_unsubscribe') as mock_process:
            mock_process.return_value = (False, "Invalid or expired unsubscribe token")
            
            response = lambda_handler(event, None)
            
            assert response['statusCode'] == 400
            body = json.loads(response['body'])
            assert body['success'] is False
            assert 'invalid' in body['message'].lower()
    
    def test_missing_token(self):
        """Test request with missing token"""
        event = {
            'body': json.dumps({})
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'missing' in body['message'].lower()
    
    def test_empty_token(self):
        """Test request with empty token"""
        event = {
            'body': json.dumps({
                'token': ''
            })
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'missing' in body['message'].lower()
    
    def test_whitespace_token(self):
        """Test request with whitespace-only token"""
        event = {
            'body': json.dumps({
                'token': '   '
            })
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['success'] is False
    
    def test_invalid_json(self):
        """Test request with invalid JSON"""
        event = {
            'body': 'not valid json'
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'json' in body['message'].lower()
    
    def test_dict_body(self):
        """Test request with dict body (not string)"""
        event = {
            'body': {
                'token': 'valid-token-12345678'
            }
        }
        
        with patch('src.unsubscribe.handler.process_unsubscribe') as mock_process:
            mock_process.return_value = (True, "Successfully unsubscribed")
            
            response = lambda_handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['success'] is True
    
    def test_cors_headers(self):
        """Test that CORS headers are present"""
        event = {
            'body': json.dumps({
                'token': 'test-token'
            })
        }
        
        with patch('src.unsubscribe.handler.process_unsubscribe') as mock_process:
            mock_process.return_value = (True, "Success")
            
            response = lambda_handler(event, None)
            
            assert 'Access-Control-Allow-Origin' in response['headers']
            assert response['headers']['Access-Control-Allow-Origin'] == '*'
            assert response['headers']['Content-Type'] == 'application/json'
    
    def test_unexpected_error(self):
        """Test handling of unexpected errors"""
        event = {
            'body': json.dumps({
                'token': 'test-token'
            })
        }
        
        with patch('src.unsubscribe.handler.process_unsubscribe') as mock_process:
            mock_process.side_effect = Exception("Unexpected error")
            
            response = lambda_handler(event, None)
            
            assert response['statusCode'] == 500
            body = json.loads(response['body'])
            assert body['success'] is False
            assert 'internal server error' in body['message'].lower()
    
    def test_already_unsubscribed(self):
        """Test unsubscribing already inactive subscriber"""
        event = {
            'body': json.dumps({
                'token': 'valid-token-12345678'
            })
        }
        
        with patch('src.unsubscribe.handler.process_unsubscribe') as mock_process:
            mock_process.return_value = (True, "You have already been unsubscribed")
            
            response = lambda_handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['success'] is True
            assert 'already' in body['message'].lower()


class TestRequirementValidation:
    """Test that requirements are properly validated in handler"""
    
    def test_requirement_11_5_validation_before_processing(self):
        """
        Requirement 11.5: THE System SHALL validate the unsubscribe_token 
        before processing unsubscribe requests
        """
        # Test that missing token is rejected before processing
        event = {'body': json.dumps({})}
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['success'] is False
        
        # Test that empty token is rejected before processing
        event = {'body': json.dumps({'token': ''})}
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['success'] is False
