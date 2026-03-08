"""
Unit tests for Get Sample Newsletter Lambda handler
"""
import json
import pytest
from unittest.mock import patch
from src.get_sample.handler import lambda_handler


class TestLambdaHandler:
    """Tests for lambda_handler function"""

    @patch('src.get_sample.handler.get_latest_newsletter_from_s3')
    def test_successful_retrieval(self, mock_get_latest):
        """Test successful retrieval returns JSON with html_content"""
        html_content = '<html><body><h1>Test Newsletter</h1></body></html>'
        mock_get_latest.return_value = html_content

        result = lambda_handler({}, None)

        assert result['statusCode'] == 200
        assert result['headers']['Content-Type'] == 'application/json'
        assert result['headers']['Access-Control-Allow-Origin'] == '*'
        body = json.loads(result['body'])
        assert body['success'] is True
        assert body['html_content'] == html_content
        mock_get_latest.assert_called_once()

    @patch('src.get_sample.handler.get_latest_newsletter_from_s3')
    def test_no_newsletter_available(self, mock_get_latest):
        """Test 404 JSON response when no newsletter in S3"""
        mock_get_latest.return_value = None

        result = lambda_handler({}, None)

        assert result['statusCode'] == 404
        assert result['headers']['Access-Control-Allow-Origin'] == '*'
        body = json.loads(result['body'])
        assert body['success'] is False
        mock_get_latest.assert_called_once()

    @patch('src.get_sample.handler.get_latest_newsletter_from_s3')
    def test_cors_headers_present(self, mock_get_latest):
        """Test that CORS headers are always present"""
        mock_get_latest.return_value = '<html><body>Test</body></html>'

        result = lambda_handler({}, None)

        headers = result['headers']
        assert headers['Access-Control-Allow-Origin'] == '*'
        assert 'GET' in headers['Access-Control-Allow-Methods']
        assert 'Content-Type' in headers['Access-Control-Allow-Headers']

    @patch('src.get_sample.handler.get_latest_newsletter_from_s3')
    def test_content_type_is_json(self, mock_get_latest):
        """Test that Content-Type is application/json"""
        mock_get_latest.return_value = '<html><body>Test</body></html>'

        result = lambda_handler({}, None)

        assert result['headers']['Content-Type'] == 'application/json'
