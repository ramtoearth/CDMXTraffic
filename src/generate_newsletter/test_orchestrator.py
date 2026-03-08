"""
Unit tests for newsletter orchestration

Tests the orchestration logic for invoking Scraper and AI Generator Lambdas
"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.generate_newsletter.orchestrator import (
    invoke_scraper_lambda,
    invoke_ai_generator_lambda,
    generate_and_send_daily_newsletter,
    archive_newsletter_to_s3
)


class TestInvokeScraperLambda:
    """Tests for invoke_scraper_lambda function"""
    
    @patch('src.generate_newsletter.orchestrator.get_lambda_client')
    @patch.dict('os.environ', {'SCRAPER_FUNCTION_NAME': 'test-scraper-function'})
    def test_successful_invocation(self, mock_get_client):
        """Test successful Scraper Lambda invocation"""
        # Setup mock response
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        scraper_response = {
            'incidents': [
                {
                    'incident_id': '123',
                    'type': 'accident',
                    'location': 'Insurgentes Sur',
                    'description': 'Choque múltiple',
                    'severity': 'high',
                    'timestamp': '2024-01-15T10:00:00',
                    'source': 'ovial_cdmx'
                }
            ],
            'scraped_at': '2024-01-15T10:00:00',
            'sources_count': 2,
            'incidents_count': 1
        }
        
        mock_client.invoke.return_value = {
            'StatusCode': 200,
            'Payload': MagicMock(read=lambda: json.dumps({
                'statusCode': 200,
                'body': json.dumps(scraper_response)
            }).encode())
        }
        
        # Execute
        result = invoke_scraper_lambda()
        
        # Verify
        assert result['incidents_count'] == 1
        assert result['sources_count'] == 2
        assert len(result['incidents']) == 1
        assert result['incidents'][0]['type'] == 'accident'
        
        # Verify Lambda was invoked correctly
        mock_client.invoke.assert_called_once()
        call_args = mock_client.invoke.call_args
        assert call_args[1]['FunctionName'] == 'test-scraper-function'
        assert call_args[1]['InvocationType'] == 'RequestResponse'
    
    @patch.dict('os.environ', {}, clear=True)
    def test_missing_environment_variable(self):
        """Test error when SCRAPER_FUNCTION_NAME is not set"""
        with pytest.raises(ValueError, match="SCRAPER_FUNCTION_NAME not configured"):
            invoke_scraper_lambda()
    
    @patch('src.generate_newsletter.orchestrator.get_lambda_client')
    @patch.dict('os.environ', {'SCRAPER_FUNCTION_NAME': 'test-scraper-function'})
    def test_lambda_invocation_failure(self, mock_get_client):
        """Test handling of Lambda invocation failure"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        # Simulate Lambda invocation failure
        mock_client.invoke.return_value = {
            'StatusCode': 500,
            'Payload': MagicMock(read=lambda: b'{}')
        }
        
        with pytest.raises(Exception, match="Scraper Lambda invocation failed"):
            invoke_scraper_lambda()


class TestInvokeAIGeneratorLambda:
    """Tests for invoke_ai_generator_lambda function"""
    
    @patch('src.generate_newsletter.orchestrator.get_lambda_client')
    @patch.dict('os.environ', {'AI_GENERATOR_FUNCTION_NAME': 'test-ai-generator-function'})
    def test_successful_invocation(self, mock_get_client):
        """Test successful AI Generator Lambda invocation"""
        # Setup mock response
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        ai_response = {
            'html_body': '<html><body>Newsletter content</body></html>',
            'text_body': 'Newsletter content',
            'subject': 'Traffic Update - Jan 15',
            'summary': 'One major accident reported',
            'highlights': ['Accident on Insurgentes Sur', 'Heavy traffic expected']
        }
        
        mock_client.invoke.return_value = {
            'StatusCode': 200,
            'Payload': MagicMock(read=lambda: json.dumps(ai_response).encode())
        }
        
        # Execute
        incidents = [{'type': 'accident', 'location': 'Test'}]
        result = invoke_ai_generator_lambda(incidents)
        
        # Verify
        assert result['subject'] == 'Traffic Update - Jan 15'
        assert len(result['highlights']) == 2
        assert 'html_body' in result
        assert 'text_body' in result
        
        # Verify Lambda was invoked correctly
        mock_client.invoke.assert_called_once()
        call_args = mock_client.invoke.call_args
        assert call_args[1]['FunctionName'] == 'test-ai-generator-function'
        assert call_args[1]['InvocationType'] == 'RequestResponse'
        
        # Verify payload contains incidents
        payload = json.loads(call_args[1]['Payload'])
        assert 'incidents' in payload
        assert len(payload['incidents']) == 1
    
    @patch.dict('os.environ', {}, clear=True)
    def test_missing_environment_variable(self):
        """Test error when AI_GENERATOR_FUNCTION_NAME is not set"""
        with pytest.raises(ValueError, match="AI_GENERATOR_FUNCTION_NAME not configured"):
            invoke_ai_generator_lambda([])
    
    @patch('src.generate_newsletter.orchestrator.get_lambda_client')
    @patch.dict('os.environ', {'AI_GENERATOR_FUNCTION_NAME': 'test-ai-generator-function'})
    def test_missing_required_fields(self, mock_get_client):
        """Test error when AI Generator response is missing required fields"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        # Response missing 'highlights' field
        incomplete_response = {
            'html_body': '<html></html>',
            'text_body': 'text',
            'subject': 'subject',
            'summary': 'summary'
        }
        
        mock_client.invoke.return_value = {
            'StatusCode': 200,
            'Payload': MagicMock(read=lambda: json.dumps(incomplete_response).encode())
        }
        
        with pytest.raises(Exception, match="missing highlights"):
            invoke_ai_generator_lambda([])


class TestArchiveNewsletterToS3:
    """Tests for archive_newsletter_to_s3 function"""
    
    @patch('src.generate_newsletter.orchestrator.get_s3_client')
    @patch.dict('os.environ', {'NEWSLETTER_BUCKET': 'test-newsletter-bucket'})
    def test_successful_archive(self, mock_get_client):
        """Test successful newsletter archiving to S3"""
        # Setup mock
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.put_object.return_value = {}
        
        # Execute
        html_content = '<html><body>Test Newsletter</body></html>'
        newsletter_id = 'test-id-123'
        created_at = datetime(2024, 1, 15, 10, 30, 0)
        
        result = archive_newsletter_to_s3(html_content, newsletter_id, created_at)
        
        # Verify
        assert result == 'test-id-123'
        
        # Verify S3 put_object was called correctly
        mock_client.put_object.assert_called_once()
        call_args = mock_client.put_object.call_args[1]
        
        assert call_args['Bucket'] == 'test-newsletter-bucket'
        assert call_args['Key'] == 'newsletters/2024/01/15/test-id-123.html'
        assert call_args['Body'] == html_content.encode('utf-8')
        assert call_args['ContentType'] == 'text/html'
        assert call_args['ACL'] == 'public-read'
    
    @patch('src.generate_newsletter.orchestrator.get_s3_client')
    @patch.dict('os.environ', {'NEWSLETTER_BUCKET': 'test-newsletter-bucket'})
    def test_auto_generate_newsletter_id(self, mock_get_client):
        """Test that newsletter_id is auto-generated if not provided"""
        # Setup mock
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.put_object.return_value = {}
        
        # Execute without newsletter_id
        html_content = '<html><body>Test</body></html>'
        result = archive_newsletter_to_s3(html_content)
        
        # Verify a UUID was generated
        assert result is not None
        assert len(result) == 36  # UUID format
        assert '-' in result
    
    @patch('src.generate_newsletter.orchestrator.get_s3_client')
    @patch.dict('os.environ', {'NEWSLETTER_BUCKET': 'test-newsletter-bucket'})
    def test_correct_s3_key_format(self, mock_get_client):
        """Test that S3 key follows newsletters/YYYY/MM/DD/{newsletter_id}.html format"""
        # Setup mock
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.put_object.return_value = {}
        
        # Execute with specific date
        html_content = '<html><body>Test</body></html>'
        newsletter_id = 'abc-123'
        created_at = datetime(2024, 3, 5, 14, 0, 0)
        
        archive_newsletter_to_s3(html_content, newsletter_id, created_at)
        
        # Verify key format
        call_args = mock_client.put_object.call_args[1]
        assert call_args['Key'] == 'newsletters/2024/03/05/abc-123.html'
    
    @patch.dict('os.environ', {}, clear=True)
    def test_missing_bucket_environment_variable(self):
        """Test that function returns None when NEWSLETTER_BUCKET is not set"""
        html_content = '<html><body>Test</body></html>'
        result = archive_newsletter_to_s3(html_content)
        
        # Should return None instead of raising exception
        assert result is None
    
    @patch('src.generate_newsletter.orchestrator.get_s3_client')
    @patch('time.sleep')  # Mock sleep to speed up test
    @patch.dict('os.environ', {'NEWSLETTER_BUCKET': 'test-newsletter-bucket'})
    def test_retry_on_client_error(self, mock_sleep, mock_get_client):
        """Test retry logic on S3 ClientError"""
        from botocore.exceptions import ClientError
        
        # Setup mock to fail twice then succeed
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        error_response = {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service unavailable'}}
        mock_client.put_object.side_effect = [
            ClientError(error_response, 'PutObject'),
            ClientError(error_response, 'PutObject'),
            {}  # Success on third attempt
        ]
        
        # Execute
        html_content = '<html><body>Test</body></html>'
        newsletter_id = 'test-id'
        result = archive_newsletter_to_s3(html_content, newsletter_id)
        
        # Verify
        assert result == 'test-id'
        assert mock_client.put_object.call_count == 3
        assert mock_sleep.call_count == 2  # Slept twice before retries
    
    @patch('src.generate_newsletter.orchestrator.get_s3_client')
    @patch('time.sleep')  # Mock sleep to speed up test
    @patch.dict('os.environ', {'NEWSLETTER_BUCKET': 'test-newsletter-bucket'})
    def test_returns_none_after_max_retries(self, mock_sleep, mock_get_client):
        """Test that function returns None after 3 failed retries"""
        from botocore.exceptions import ClientError
        
        # Setup mock to always fail
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        error_response = {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}
        mock_client.put_object.side_effect = ClientError(error_response, 'PutObject')
        
        # Execute
        html_content = '<html><body>Test</body></html>'
        newsletter_id = 'test-id'
        result = archive_newsletter_to_s3(html_content, newsletter_id)
        
        # Verify
        assert result is None  # Should return None, not raise exception
        assert mock_client.put_object.call_count == 3  # Tried 3 times
        assert mock_sleep.call_count == 2  # Slept twice (not after last attempt)
    
    @patch('src.generate_newsletter.orchestrator.get_s3_client')
    @patch('time.sleep')
    @patch.dict('os.environ', {'NEWSLETTER_BUCKET': 'test-newsletter-bucket'})
    def test_exponential_backoff(self, mock_sleep, mock_get_client):
        """Test that retry delays follow exponential backoff (1s, 2s)"""
        from botocore.exceptions import ClientError
        
        # Setup mock to fail twice then succeed
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        error_response = {'Error': {'Code': 'Throttling', 'Message': 'Rate exceeded'}}
        mock_client.put_object.side_effect = [
            ClientError(error_response, 'PutObject'),
            ClientError(error_response, 'PutObject'),
            {}  # Success
        ]
        
        # Execute
        html_content = '<html><body>Test</body></html>'
        archive_newsletter_to_s3(html_content)
        
        # Verify exponential backoff: 1s, 2s
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)  # First retry delay
        mock_sleep.assert_any_call(2)  # Second retry delay
    
    @patch('src.generate_newsletter.orchestrator.get_s3_client')
    @patch('time.sleep')
    @patch.dict('os.environ', {'NEWSLETTER_BUCKET': 'test-newsletter-bucket'})
    def test_handles_unexpected_exception(self, mock_sleep, mock_get_client):
        """Test handling of unexpected exceptions (non-ClientError)"""
        # Setup mock to raise unexpected exception
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        mock_client.put_object.side_effect = ValueError("Unexpected error")
        
        # Execute
        html_content = '<html><body>Test</body></html>'
        newsletter_id = 'test-id'
        result = archive_newsletter_to_s3(html_content, newsletter_id)
        
        # Verify
        assert result is None  # Should return None, not raise exception
        assert mock_client.put_object.call_count == 3  # Tried 3 times


class TestGenerateAndSendDailyNewsletter:
    """Tests for generate_and_send_daily_newsletter orchestration function"""
    
    @patch('src.generate_newsletter.orchestrator.archive_newsletter_to_s3')
    @patch('src.generate_newsletter.orchestrator.invoke_ai_generator_lambda')
    @patch('src.generate_newsletter.orchestrator.invoke_scraper_lambda')
    def test_successful_orchestration(self, mock_scraper, mock_ai_gen, mock_archive):
        """Test successful end-to-end orchestration"""
        # Setup mocks
        mock_scraper.return_value = {
            'incidents': [
                {
                    'incident_id': '123',
                    'type': 'accident',
                    'location': 'Insurgentes Sur',
                    'description': 'Choque',
                    'severity': 'high',
                    'timestamp': '2024-01-15T10:00:00',
                    'source': 'ovial_cdmx'
                }
            ],
            'scraped_at': '2024-01-15T10:00:00',
            'sources_count': 2,
            'incidents_count': 1
        }
        
        mock_ai_gen.return_value = {
            'html_body': '<html>Newsletter</html>',
            'text_body': 'Newsletter',
            'subject': 'Traffic Update',
            'summary': 'One accident',
            'highlights': ['Accident on Insurgentes']
        }
        
        mock_archive.return_value = 'archived-newsletter-id-123'
        
        # Execute
        result = generate_and_send_daily_newsletter()
        
        # Verify
        assert result['incidents_count'] == 1
        assert result['subject'] == 'Traffic Update'
        assert result['highlights_count'] == 1
        assert result['newsletter_id'] == 'archived-newsletter-id-123'
        
        # Verify all components were invoked
        mock_scraper.assert_called_once()
        mock_ai_gen.assert_called_once()
        mock_archive.assert_called_once()
        
        # Verify AI Generator received incidents from Scraper
        ai_gen_call_args = mock_ai_gen.call_args[0]
        assert len(ai_gen_call_args[0]) == 1
        assert ai_gen_call_args[0][0]['type'] == 'accident'
        
        # Verify archive was called with HTML content
        archive_call_args = mock_archive.call_args[0]
        assert archive_call_args[0] == '<html>Newsletter</html>'
    
    @patch('src.generate_newsletter.orchestrator.archive_newsletter_to_s3')
    @patch('src.generate_newsletter.orchestrator.invoke_ai_generator_lambda')
    @patch('src.generate_newsletter.orchestrator.invoke_scraper_lambda')
    def test_continues_when_archiving_fails(self, mock_scraper, mock_ai_gen, mock_archive):
        """Test that orchestration continues when S3 archiving fails"""
        # Setup mocks
        mock_scraper.return_value = {
            'incidents': [{'type': 'accident', 'location': 'Test'}],
            'scraped_at': '2024-01-15T10:00:00',
            'sources_count': 1,
            'incidents_count': 1
        }
        
        mock_ai_gen.return_value = {
            'html_body': '<html>Newsletter</html>',
            'text_body': 'Newsletter',
            'subject': 'Traffic Update',
            'summary': 'One accident',
            'highlights': ['Accident']
        }
        
        # Simulate S3 archiving failure
        mock_archive.return_value = None
        
        # Execute - should not raise exception
        result = generate_and_send_daily_newsletter()
        
        # Verify
        assert result['newsletter_id'] is not None  # Fallback ID generated
        assert len(result['newsletter_id']) == 36  # UUID format
        assert result['incidents_count'] == 1
        
        # Verify all components were still invoked
        mock_scraper.assert_called_once()
        mock_ai_gen.assert_called_once()
        mock_archive.assert_called_once()
    
    @patch('src.generate_newsletter.orchestrator.invoke_scraper_lambda')
    def test_scraper_failure_propagates(self, mock_scraper):
        """Test that Scraper Lambda failure propagates correctly"""
        mock_scraper.side_effect = Exception("Scraper failed")
        
        with pytest.raises(Exception, match="Scraper failed"):
            generate_and_send_daily_newsletter()
    
    @patch('src.generate_newsletter.orchestrator.archive_newsletter_to_s3')
    @patch('src.generate_newsletter.orchestrator.invoke_ai_generator_lambda')
    @patch('src.generate_newsletter.orchestrator.invoke_scraper_lambda')
    def test_ai_generator_failure_propagates(self, mock_scraper, mock_ai_gen, mock_archive):
        """Test that AI Generator Lambda failure propagates correctly"""
        mock_scraper.return_value = {
            'incidents': [],
            'scraped_at': '2024-01-15T10:00:00',
            'sources_count': 2,
            'incidents_count': 0
        }
        
        mock_ai_gen.side_effect = Exception("AI Generator failed")
        
        with pytest.raises(Exception, match="AI Generator failed"):
            generate_and_send_daily_newsletter()
    
    @patch('src.generate_newsletter.orchestrator.archive_newsletter_to_s3')
    @patch('src.generate_newsletter.orchestrator.invoke_ai_generator_lambda')
    @patch('src.generate_newsletter.orchestrator.invoke_scraper_lambda')
    def test_empty_incidents_handled(self, mock_scraper, mock_ai_gen, mock_archive):
        """Test orchestration with no incidents (empty list)"""
        # Setup mocks for empty incidents
        mock_scraper.return_value = {
            'incidents': [],
            'scraped_at': '2024-01-15T10:00:00',
            'sources_count': 2,
            'incidents_count': 0
        }
        
        mock_ai_gen.return_value = {
            'html_body': '<html>No incidents today</html>',
            'text_body': 'No incidents today',
            'subject': 'No Traffic Incidents Today',
            'summary': 'No incidents reported',
            'highlights': ['No incidents today']
        }
        
        mock_archive.return_value = 'newsletter-id-empty'
        
        # Execute
        result = generate_and_send_daily_newsletter()
        
        # Verify
        assert result['incidents_count'] == 0
        assert result['subject'] == 'No Traffic Incidents Today'
        
        # Verify AI Generator was still called with empty list
        mock_ai_gen.assert_called_once_with([])
        
        # Verify archive was still called
        mock_archive.assert_called_once()
    @patch('src.generate_newsletter.orchestrator.log_newsletter_metrics')
    @patch('src.generate_newsletter.orchestrator.update_subscriber_last_sent')
    @patch('src.generate_newsletter.orchestrator.invoke_send_email_lambda')
    @patch('src.generate_newsletter.orchestrator.get_active_subscribers_by_frequency')
    @patch('src.generate_newsletter.orchestrator.archive_newsletter_to_s3')
    @patch('src.generate_newsletter.orchestrator.invoke_ai_generator_lambda')
    @patch('src.generate_newsletter.orchestrator.invoke_scraper_lambda')
    def test_complete_orchestration_with_subscribers(
        self, mock_scraper, mock_ai_gen, mock_archive,
        mock_get_subscribers, mock_send_email, mock_update_last_sent, mock_log_metrics
    ):
        """Test complete end-to-end orchestration including subscriber sending"""
        # Setup mocks
        mock_scraper.return_value = {
            'incidents': [
                {
                    'incident_id': '123',
                    'type': 'accident',
                    'location': 'Insurgentes Sur',
                    'description': 'Choque',
                    'severity': 'high',
                    'timestamp': '2024-01-15T10:00:00',
                    'source': 'ovial_cdmx'
                }
            ],
            'scraped_at': '2024-01-15T10:00:00',
            'sources_count': 2,
            'incidents_count': 1
        }

        mock_ai_gen.return_value = {
            'html_body': '<html>Newsletter</html>',
            'text_body': 'Newsletter',
            'subject': 'Traffic Update',
            'summary': 'One accident',
            'highlights': ['Accident on Insurgentes']
        }

        mock_archive.return_value = 'newsletter-id-123'

        # Mock 3 subscribers
        mock_get_subscribers.return_value = [
            {
                'subscriber_id': 'sub-1',
                'email': 'user1@example.com',
                'name': 'User One',
                'frequency': 'daily',
                'active': True
            },
            {
                'subscriber_id': 'sub-2',
                'email': 'user2@example.com',
                'name': 'User Two',
                'frequency': 'daily',
                'active': True
            },
            {
                'subscriber_id': 'sub-3',
                'email': 'user3@example.com',
                'name': 'User Three',
                'frequency': 'daily',
                'active': True
            }
        ]

        # Mock email sending - 2 succeed, 1 fails
        mock_send_email.side_effect = [
            {'success': True, 'message_id': 'msg-1'},
            {'success': True, 'message_id': 'msg-2'},
            {'success': False, 'error': 'Invalid email'}
        ]

        mock_update_last_sent.return_value = True

        # Execute
        result = generate_and_send_daily_newsletter()

        # Verify result
        assert result['newsletter_id'] == 'newsletter-id-123'
        assert result['sent_count'] == 2
        assert result['failed_count'] == 1
        assert result['incidents_count'] == 1

        # Verify all components were invoked
        mock_scraper.assert_called_once()
        mock_ai_gen.assert_called_once()
        mock_archive.assert_called_once()
        mock_get_subscribers.assert_called_once_with('daily')

        # Verify email was sent to all 3 subscribers
        assert mock_send_email.call_count == 3

        # Verify last_sent_at was updated for successful sends only
        assert mock_update_last_sent.call_count == 2
        mock_update_last_sent.assert_any_call('sub-1')
        mock_update_last_sent.assert_any_call('sub-2')

        # Verify metrics were logged
        mock_log_metrics.assert_called_once_with('newsletter-id-123', 2, 1, 1)

    @patch('src.generate_newsletter.orchestrator.log_newsletter_metrics')
    @patch('src.generate_newsletter.orchestrator.get_active_subscribers_by_frequency')
    @patch('src.generate_newsletter.orchestrator.archive_newsletter_to_s3')
    @patch('src.generate_newsletter.orchestrator.invoke_ai_generator_lambda')
    @patch('src.generate_newsletter.orchestrator.invoke_scraper_lambda')
    def test_orchestration_with_no_subscribers(
        self, mock_scraper, mock_ai_gen, mock_archive,
        mock_get_subscribers, mock_log_metrics
    ):
        """Test orchestration when there are no active subscribers"""
        # Setup mocks
        mock_scraper.return_value = {
            'incidents': [{'type': 'accident', 'location': 'Test'}],
            'scraped_at': '2024-01-15T10:00:00',
            'sources_count': 1,
            'incidents_count': 1
        }

        mock_ai_gen.return_value = {
            'html_body': '<html>Newsletter</html>',
            'text_body': 'Newsletter',
            'subject': 'Traffic Update',
            'summary': 'One accident',
            'highlights': ['Accident']
        }

        mock_archive.return_value = 'newsletter-id-123'

        # No subscribers
        mock_get_subscribers.return_value = []

        # Execute
        result = generate_and_send_daily_newsletter()

        # Verify
        assert result['newsletter_id'] == 'newsletter-id-123'
        assert result['sent_count'] == 0
        assert result['failed_count'] == 0
        assert result['incidents_count'] == 1

        # Verify metrics were logged with 0 counts
        mock_log_metrics.assert_called_once_with('newsletter-id-123', 0, 0, 1)

    @patch('src.generate_newsletter.orchestrator.log_newsletter_metrics')
    @patch('src.generate_newsletter.orchestrator.update_subscriber_last_sent')
    @patch('src.generate_newsletter.orchestrator.invoke_send_email_lambda')
    @patch('src.generate_newsletter.orchestrator.get_active_subscribers_by_frequency')
    @patch('src.generate_newsletter.orchestrator.archive_newsletter_to_s3')
    @patch('src.generate_newsletter.orchestrator.invoke_ai_generator_lambda')
    @patch('src.generate_newsletter.orchestrator.invoke_scraper_lambda')
    def test_continues_sending_after_individual_failures(
        self, mock_scraper, mock_ai_gen, mock_archive,
        mock_get_subscribers, mock_send_email, mock_update_last_sent, mock_log_metrics
    ):
        """Test that orchestration continues sending to other subscribers after individual failures"""
        # Setup mocks
        mock_scraper.return_value = {
            'incidents': [],
            'scraped_at': '2024-01-15T10:00:00',
            'sources_count': 1,
            'incidents_count': 0
        }

        mock_ai_gen.return_value = {
            'html_body': '<html>No incidents</html>',
            'text_body': 'No incidents',
            'subject': 'No Traffic Issues',
            'summary': 'No incidents',
            'highlights': ['No incidents today']
        }

        mock_archive.return_value = 'newsletter-id-123'

        # Mock 5 subscribers
        mock_get_subscribers.return_value = [
            {'subscriber_id': f'sub-{i}', 'email': f'user{i}@example.com', 'name': f'User {i}'}
            for i in range(1, 6)
        ]

        # Mock email sending - alternating success/failure
        mock_send_email.side_effect = [
            {'success': True, 'message_id': 'msg-1'},
            {'success': False, 'error': 'Rate limit'},
            {'success': True, 'message_id': 'msg-3'},
            {'success': False, 'error': 'Invalid email'},
            {'success': True, 'message_id': 'msg-5'}
        ]

        mock_update_last_sent.return_value = True

        # Execute
        result = generate_and_send_daily_newsletter()

        # Verify all subscribers were attempted
        assert mock_send_email.call_count == 5

        # Verify correct counts
        assert result['sent_count'] == 3
        assert result['failed_count'] == 2

        # Verify last_sent_at was updated only for successful sends
        assert mock_update_last_sent.call_count == 3



    class TestGetActiveSubscribersByFrequency:
        """Tests for get_active_subscribers_by_frequency function"""

        @patch('src.generate_newsletter.orchestrator.get_dynamodb_resource')
        @patch.dict('os.environ', {'SUBSCRIBERS_TABLE': 'test-subscribers-table'})
        def test_successful_query(self, mock_get_resource):
            """Test successful query for active daily subscribers"""
            # Setup mock
            mock_table = Mock()
            mock_resource = Mock()
            mock_resource.Table.return_value = mock_table
            mock_get_resource.return_value = mock_resource

            # Mock DynamoDB response
            mock_table.query.return_value = {
                'Items': [
                    {
                        'subscriber_id': 'sub-1',
                        'email': 'user1@example.com',
                        'name': 'User One',
                        'frequency': 'daily',
                        'active': True,
                        'subscribed_at': '2024-01-01T10:00:00',
                        'last_sent_at': None,
                        'unsubscribe_token': 'token-1'
                    },
                    {
                        'subscriber_id': 'sub-2',
                        'email': 'user2@example.com',
                        'name': 'User Two',
                        'frequency': 'daily',
                        'active': True,
                        'subscribed_at': '2024-01-02T10:00:00',
                        'last_sent_at': '2024-01-10T07:00:00',
                        'unsubscribe_token': 'token-2'
                    }
                ]
            }

            # Execute
            from src.generate_newsletter.orchestrator import get_active_subscribers_by_frequency
            result = get_active_subscribers_by_frequency('daily')

            # Verify
            assert len(result) == 2
            assert result[0]['email'] == 'user1@example.com'
            assert result[1]['email'] == 'user2@example.com'

            # Verify query was called correctly
            mock_table.query.assert_called_once()
            call_args = mock_table.query.call_args[1]
            assert call_args['IndexName'] == 'frequency-active-index'
            assert call_args['ExpressionAttributeValues'][':freq'] == 'daily'
            assert call_args['ExpressionAttributeValues'][':active'] == 'true'

        @patch('src.generate_newsletter.orchestrator.get_dynamodb_resource')
        @patch.dict('os.environ', {'SUBSCRIBERS_TABLE': 'test-subscribers-table'})
        def test_pagination_handling(self, mock_get_resource):
            """Test that pagination is handled correctly"""
            # Setup mock
            mock_table = Mock()
            mock_resource = Mock()
            mock_resource.Table.return_value = mock_table
            mock_get_resource.return_value = mock_resource

            # Mock paginated responses
            mock_table.query.side_effect = [
                {
                    'Items': [{'subscriber_id': 'sub-1', 'email': 'user1@example.com'}],
                    'LastEvaluatedKey': {'subscriber_id': 'sub-1'}
                },
                {
                    'Items': [{'subscriber_id': 'sub-2', 'email': 'user2@example.com'}]
                }
            ]

            # Execute
            from src.generate_newsletter.orchestrator import get_active_subscribers_by_frequency
            result = get_active_subscribers_by_frequency('daily')

            # Verify
            assert len(result) == 2
            assert mock_table.query.call_count == 2

        @patch.dict('os.environ', {}, clear=True)
        def test_missing_environment_variable(self):
            """Test error when SUBSCRIBERS_TABLE is not set"""
            from src.generate_newsletter.orchestrator import get_active_subscribers_by_frequency
            result = get_active_subscribers_by_frequency('daily')

            # Should return empty list instead of raising exception
            assert result == []

        @patch('src.generate_newsletter.orchestrator.get_dynamodb_resource')
        @patch.dict('os.environ', {'SUBSCRIBERS_TABLE': 'test-subscribers-table'})
        def test_empty_result(self, mock_get_resource):
            """Test handling of no subscribers found"""
            # Setup mock
            mock_table = Mock()
            mock_resource = Mock()
            mock_resource.Table.return_value = mock_table
            mock_get_resource.return_value = mock_resource

            mock_table.query.return_value = {'Items': []}

            # Execute
            from src.generate_newsletter.orchestrator import get_active_subscribers_by_frequency
            result = get_active_subscribers_by_frequency('daily')

            # Verify
            assert result == []

        @patch('src.generate_newsletter.orchestrator.get_dynamodb_resource')
        @patch.dict('os.environ', {'SUBSCRIBERS_TABLE': 'test-subscribers-table'})
        def test_client_error_handling(self, mock_get_resource):
            """Test handling of DynamoDB ClientError"""
            from botocore.exceptions import ClientError

            # Setup mock to raise error
            mock_table = Mock()
            mock_resource = Mock()
            mock_resource.Table.return_value = mock_table
            mock_get_resource.return_value = mock_resource

            error_response = {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Table not found'}}
            mock_table.query.side_effect = ClientError(error_response, 'Query')

            # Execute
            from src.generate_newsletter.orchestrator import get_active_subscribers_by_frequency
            result = get_active_subscribers_by_frequency('daily')

            # Should return empty list instead of raising exception
            assert result == []


    class TestUpdateSubscriberLastSent:
        """Tests for update_subscriber_last_sent function"""

        @patch('src.generate_newsletter.orchestrator.get_dynamodb_resource')
        @patch.dict('os.environ', {'SUBSCRIBERS_TABLE': 'test-subscribers-table'})
        def test_successful_update(self, mock_get_resource):
            """Test successful update of last_sent_at timestamp"""
            # Setup mock
            mock_table = Mock()
            mock_resource = Mock()
            mock_resource.Table.return_value = mock_table
            mock_get_resource.return_value = mock_resource

            mock_table.update_item.return_value = {}

            # Execute
            from src.generate_newsletter.orchestrator import update_subscriber_last_sent
            result = update_subscriber_last_sent('sub-123')

            # Verify
            assert result is True

            # Verify update_item was called correctly
            mock_table.update_item.assert_called_once()
            call_args = mock_table.update_item.call_args[1]
            assert call_args['Key'] == {'subscriber_id': 'sub-123'}
            assert call_args['UpdateExpression'] == 'SET last_sent_at = :timestamp'
            assert ':timestamp' in call_args['ExpressionAttributeValues']

        @patch.dict('os.environ', {}, clear=True)
        def test_missing_environment_variable(self):
            """Test error when SUBSCRIBERS_TABLE is not set"""
            from src.generate_newsletter.orchestrator import update_subscriber_last_sent
            result = update_subscriber_last_sent('sub-123')

            # Should return False instead of raising exception
            assert result is False

        @patch('src.generate_newsletter.orchestrator.get_dynamodb_resource')
        @patch.dict('os.environ', {'SUBSCRIBERS_TABLE': 'test-subscribers-table'})
        def test_client_error_handling(self, mock_get_resource):
            """Test handling of DynamoDB ClientError"""
            from botocore.exceptions import ClientError

            # Setup mock to raise error
            mock_table = Mock()
            mock_resource = Mock()
            mock_resource.Table.return_value = mock_table
            mock_get_resource.return_value = mock_resource

            error_response = {'Error': {'Code': 'ConditionalCheckFailedException', 'Message': 'Item not found'}}
            mock_table.update_item.side_effect = ClientError(error_response, 'UpdateItem')

            # Execute
            from src.generate_newsletter.orchestrator import update_subscriber_last_sent
            result = update_subscriber_last_sent('sub-123')

            # Should return False instead of raising exception
            assert result is False


    class TestInvokeSendEmailLambda:
        """Tests for invoke_send_email_lambda function"""

        @patch('src.generate_newsletter.orchestrator.get_lambda_client')
        @patch.dict('os.environ', {'SEND_EMAIL_FUNCTION_NAME': 'test-send-email-function'})
        def test_successful_invocation(self, mock_get_client):
            """Test successful Send Email Lambda invocation"""
            # Setup mock
            mock_client = Mock()
            mock_get_client.return_value = mock_client

            email_response = {
                'success': True,
                'message_id': 'msg-123'
            }

            mock_client.invoke.return_value = {
                'StatusCode': 200,
                'Payload': MagicMock(read=lambda: json.dumps({
                    'statusCode': 200,
                    'body': json.dumps(email_response)
                }).encode())
            }

            # Execute
            from src.generate_newsletter.orchestrator import invoke_send_email_lambda
            result = invoke_send_email_lambda(
                to_email='user@example.com',
                to_name='User Name',
                subject='Test Newsletter',
                html_body='<html>Test</html>',
                text_body='Test',
                newsletter_type='daily'
            )

            # Verify
            assert result['success'] is True
            assert result['message_id'] == 'msg-123'

            # Verify Lambda was invoked correctly
            mock_client.invoke.assert_called_once()
            call_args = mock_client.invoke.call_args[1]
            assert call_args['FunctionName'] == 'test-send-email-function'
            assert call_args['InvocationType'] == 'RequestResponse'

            # Verify payload
            payload = json.loads(call_args['Payload'])
            assert payload['to_email'] == 'user@example.com'
            assert payload['to_name'] == 'User Name'
            assert payload['subject'] == 'Test Newsletter'
            assert payload['newsletter_type'] == 'daily'

        @patch.dict('os.environ', {}, clear=True)
        def test_missing_environment_variable(self):
            """Test error when SEND_EMAIL_FUNCTION_NAME is not set"""
            from src.generate_newsletter.orchestrator import invoke_send_email_lambda
            result = invoke_send_email_lambda(
                to_email='user@example.com',
                to_name='User',
                subject='Test',
                html_body='<html>Test</html>',
                text_body='Test'
            )

            # Should return error dict instead of raising exception
            assert result['success'] is False
            assert 'not configured' in result['error']

        @patch('src.generate_newsletter.orchestrator.get_lambda_client')
        @patch.dict('os.environ', {'SEND_EMAIL_FUNCTION_NAME': 'test-send-email-function'})
        def test_email_send_failure(self, mock_get_client):
            """Test handling of email send failure"""
            # Setup mock
            mock_client = Mock()
            mock_get_client.return_value = mock_client

            email_response = {
                'success': False,
                'error': 'Invalid email address'
            }

            mock_client.invoke.return_value = {
                'StatusCode': 200,
                'Payload': MagicMock(read=lambda: json.dumps({
                    'statusCode': 500,
                    'body': json.dumps(email_response)
                }).encode())
            }

            # Execute
            from src.generate_newsletter.orchestrator import invoke_send_email_lambda
            result = invoke_send_email_lambda(
                to_email='invalid@example.com',
                to_name='User',
                subject='Test',
                html_body='<html>Test</html>',
                text_body='Test'
            )

            # Verify
            assert result['success'] is False
            assert result['error'] == 'Invalid email address'


    class TestLogNewsletterMetrics:
        """Tests for log_newsletter_metrics function"""

        @patch('src.generate_newsletter.orchestrator.logger')
        def test_metrics_logging(self, mock_logger):
            """Test that metrics are logged correctly"""
            from src.generate_newsletter.orchestrator import log_newsletter_metrics

            # Execute
            log_newsletter_metrics(
                newsletter_id='newsletter-123',
                sent_count=50,
                failed_count=5,
                incidents_count=10
            )

            # Verify logger.info was called
            mock_logger.info.assert_called_once()
            log_message = mock_logger.info.call_args[0][0]

            # Verify all metrics are in the log message
            assert 'newsletter-123' in log_message
            assert 'sent_count=50' in log_message
            assert 'failed_count=5' in log_message
            assert 'incidents_count=10' in log_message
            assert 'total_subscribers=55' in log_message


