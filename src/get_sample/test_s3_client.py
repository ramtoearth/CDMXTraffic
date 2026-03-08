"""
Unit tests for S3 client functions
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from botocore.exceptions import ClientError
from src.get_sample.s3_client import get_latest_newsletter_from_s3


class TestGetLatestNewsletterFromS3:
    """Tests for get_latest_newsletter_from_s3 function"""
    
    @patch('src.get_sample.s3_client.get_s3_client')
    @patch.dict('os.environ', {'NEWSLETTER_BUCKET': 'test-newsletter-bucket'})
    def test_successful_retrieval(self, mock_get_client):
        """Test successful retrieval of latest newsletter"""
        # Setup
        mock_s3 = MagicMock()
        mock_get_client.return_value = mock_s3
        
        # Mock paginator
        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        
        # Mock list of newsletters with different timestamps
        mock_paginator.paginate.return_value = [
            {
                'Contents': [
                    {
                        'Key': 'newsletters/2024/01/15/old-newsletter.html',
                        'LastModified': datetime(2024, 1, 15, 10, 0, 0)
                    },
                    {
                        'Key': 'newsletters/2024/01/20/latest-newsletter.html',
                        'LastModified': datetime(2024, 1, 20, 10, 0, 0)
                    },
                    {
                        'Key': 'newsletters/2024/01/18/middle-newsletter.html',
                        'LastModified': datetime(2024, 1, 18, 10, 0, 0)
                    }
                ]
            }
        ]
        
        # Mock get_object response
        html_content = '<html><body>Latest Newsletter</body></html>'
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=lambda: html_content.encode('utf-8'))
        }
        
        # Execute
        result = get_latest_newsletter_from_s3()
        
        # Verify
        assert result == html_content
        mock_s3.get_paginator.assert_called_once_with('list_objects_v2')
        mock_paginator.paginate.assert_called_once_with(
            Bucket='test-newsletter-bucket',
            Prefix='newsletters/'
        )
        mock_s3.get_object.assert_called_once_with(
            Bucket='test-newsletter-bucket',
            Key='newsletters/2024/01/20/latest-newsletter.html'
        )
    
    @patch('src.get_sample.s3_client.get_s3_client')
    @patch.dict('os.environ', {'NEWSLETTER_BUCKET': 'test-newsletter-bucket'})
    def test_no_newsletters_found(self, mock_get_client):
        """Test when no newsletters exist in S3"""
        # Setup
        mock_s3 = MagicMock()
        mock_get_client.return_value = mock_s3
        
        # Mock paginator with empty results
        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{}]  # No 'Contents' key
        
        # Execute
        result = get_latest_newsletter_from_s3()
        
        # Verify
        assert result is None
        mock_s3.get_object.assert_not_called()
    
    @patch.dict('os.environ', {}, clear=True)
    def test_missing_bucket_env_var(self):
        """Test when NEWSLETTER_BUCKET environment variable is not set"""
        # Execute
        result = get_latest_newsletter_from_s3()
        
        # Verify
        assert result is None
    
    @patch('src.get_sample.s3_client.get_s3_client')
    @patch.dict('os.environ', {'NEWSLETTER_BUCKET': 'test-newsletter-bucket'})
    def test_s3_client_error(self, mock_get_client):
        """Test handling of S3 ClientError"""
        # Setup
        mock_s3 = MagicMock()
        mock_get_client.return_value = mock_s3
        
        # Mock paginator to raise ClientError
        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchBucket', 'Message': 'Bucket does not exist'}},
            'ListObjectsV2'
        )
        
        # Execute
        result = get_latest_newsletter_from_s3()
        
        # Verify
        assert result is None
    
    @patch('src.get_sample.s3_client.get_s3_client')
    @patch.dict('os.environ', {'NEWSLETTER_BUCKET': 'test-newsletter-bucket'})
    def test_unexpected_error(self, mock_get_client):
        """Test handling of unexpected errors"""
        # Setup
        mock_s3 = MagicMock()
        mock_get_client.return_value = mock_s3
        
        # Mock paginator to raise unexpected error
        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.side_effect = Exception("Unexpected error")
        
        # Execute
        result = get_latest_newsletter_from_s3()
        
        # Verify
        assert result is None
    
    @patch('src.get_sample.s3_client.get_s3_client')
    @patch.dict('os.environ', {'NEWSLETTER_BUCKET': 'test-newsletter-bucket'})
    def test_single_newsletter(self, mock_get_client):
        """Test retrieval when only one newsletter exists"""
        # Setup
        mock_s3 = MagicMock()
        mock_get_client.return_value = mock_s3
        
        # Mock paginator with single newsletter
        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                'Contents': [
                    {
                        'Key': 'newsletters/2024/01/15/only-newsletter.html',
                        'LastModified': datetime(2024, 1, 15, 10, 0, 0)
                    }
                ]
            }
        ]
        
        # Mock get_object response
        html_content = '<html><body>Only Newsletter</body></html>'
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=lambda: html_content.encode('utf-8'))
        }
        
        # Execute
        result = get_latest_newsletter_from_s3()
        
        # Verify
        assert result == html_content
        mock_s3.get_object.assert_called_once_with(
            Bucket='test-newsletter-bucket',
            Key='newsletters/2024/01/15/only-newsletter.html'
        )
    
    @patch('src.get_sample.s3_client.get_s3_client')
    @patch.dict('os.environ', {'NEWSLETTER_BUCKET': 'test-newsletter-bucket'})
    def test_pagination_multiple_pages(self, mock_get_client):
        """Test handling of paginated results"""
        # Setup
        mock_s3 = MagicMock()
        mock_get_client.return_value = mock_s3
        
        # Mock paginator with multiple pages
        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                'Contents': [
                    {
                        'Key': 'newsletters/2024/01/15/old-newsletter.html',
                        'LastModified': datetime(2024, 1, 15, 10, 0, 0)
                    }
                ]
            },
            {
                'Contents': [
                    {
                        'Key': 'newsletters/2024/01/20/latest-newsletter.html',
                        'LastModified': datetime(2024, 1, 20, 10, 0, 0)
                    }
                ]
            }
        ]
        
        # Mock get_object response
        html_content = '<html><body>Latest Newsletter</body></html>'
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=lambda: html_content.encode('utf-8'))
        }
        
        # Execute
        result = get_latest_newsletter_from_s3()
        
        # Verify
        assert result == html_content
        mock_s3.get_object.assert_called_once_with(
            Bucket='test-newsletter-bucket',
            Key='newsletters/2024/01/20/latest-newsletter.html'
        )
    
    @patch('src.get_sample.s3_client.get_s3_client')
    @patch.dict('os.environ', {'NEWSLETTER_BUCKET': 'test-newsletter-bucket'})
    def test_sorting_by_last_modified(self, mock_get_client):
        """Test that newsletters are sorted by LastModified, not by key name"""
        # Setup
        mock_s3 = MagicMock()
        mock_get_client.return_value = mock_s3
        
        # Mock paginator - keys are in alphabetical order but timestamps differ
        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                'Contents': [
                    {
                        'Key': 'newsletters/2024/01/25/a-newsletter.html',
                        'LastModified': datetime(2024, 1, 25, 8, 0, 0)  # Older timestamp
                    },
                    {
                        'Key': 'newsletters/2024/01/25/z-newsletter.html',
                        'LastModified': datetime(2024, 1, 25, 10, 0, 0)  # Newer timestamp
                    }
                ]
            }
        ]
        
        # Mock get_object response
        html_content = '<html><body>Z Newsletter (Latest)</body></html>'
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=lambda: html_content.encode('utf-8'))
        }
        
        # Execute
        result = get_latest_newsletter_from_s3()
        
        # Verify - should get z-newsletter because it has newer LastModified
        assert result == html_content
        mock_s3.get_object.assert_called_once_with(
            Bucket='test-newsletter-bucket',
            Key='newsletters/2024/01/25/z-newsletter.html'
        )
