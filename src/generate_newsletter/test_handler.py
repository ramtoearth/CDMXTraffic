"""
Unit tests for Generate Newsletter Lambda handler
"""
import json
import pytest
from unittest.mock import patch

from src.generate_newsletter.handler import lambda_handler


class TestLambdaHandler:
    """Tests for lambda_handler function"""
    
    @patch('src.generate_newsletter.handler.generate_and_send_daily_newsletter')
    def test_successful_execution(self, mock_orchestrator):
        """Test successful newsletter generation"""
        # Setup mock
        mock_orchestrator.return_value = {
            'newsletter_id': 'test-newsletter-123',
            'sent_count': 0,
            'failed_count': 0,
            'incidents_count': 5,
            'subject': 'Traffic Update - Jan 15',
            'highlights_count': 3
        }
        
        # Execute
        result = lambda_handler({}, None)
        
        # Verify
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['newsletter_id'] == 'test-newsletter-123'
        assert body['incidents_count'] == 5
        assert body['subject'] == 'Traffic Update - Jan 15'
        
        # Verify orchestrator was called
        mock_orchestrator.assert_called_once()
    
    @patch('src.generate_newsletter.handler.generate_and_send_daily_newsletter')
    def test_orchestration_failure(self, mock_orchestrator):
        """Test handling of orchestration failure"""
        # Setup mock to raise exception
        mock_orchestrator.side_effect = Exception("Scraper Lambda failed")
        
        # Execute
        result = lambda_handler({}, None)
        
        # Verify error response
        assert result['statusCode'] == 500
        body = json.loads(result['body'])
        assert 'error' in body
        assert 'Scraper Lambda failed' in body['error']
        assert body['message'] == 'Newsletter generation failed'
    
    @patch('src.generate_newsletter.handler.generate_and_send_daily_newsletter')
    def test_empty_incidents(self, mock_orchestrator):
        """Test newsletter generation with no incidents"""
        # Setup mock for empty incidents
        mock_orchestrator.return_value = {
            'newsletter_id': 'test-newsletter-456',
            'sent_count': 0,
            'failed_count': 0,
            'incidents_count': 0,
            'subject': 'No Traffic Incidents Today',
            'highlights_count': 1
        }
        
        # Execute
        result = lambda_handler({}, None)
        
        # Verify
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['incidents_count'] == 0
        assert 'No Traffic Incidents' in body['subject']

