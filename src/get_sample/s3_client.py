"""
S3 client for retrieving newsletters from archive
"""
import os
import logging
from typing import Optional
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Global S3 client for reuse across invocations
_s3_client = None


def get_s3_client():
    """Get or create S3 client (lazy initialization)"""
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client('s3')
    return _s3_client


def get_latest_newsletter_from_s3() -> Optional[str]:
    """
    Retrieves the most recent newsletter from S3 archive
    
    Returns:
        HTML content of the latest newsletter, or None if no newsletters found
        
    Requirements:
        - 8.2: Return the most recent newsletter from the S3 archive
        
    Preconditions:
        - NEWSLETTER_BUCKET environment variable is set
        - S3 bucket exists and is accessible
        - Newsletters are stored with key format: newsletters/YYYY/MM/DD/{newsletter_id}.html
        
    Postconditions:
        - Returns HTML content of the most recent newsletter
        - Returns None if no newsletters exist or on error
        - Logs errors but doesn't raise exceptions
    """
    bucket_name = os.environ.get('NEWSLETTER_BUCKET')
    if not bucket_name:
        logger.error("NEWSLETTER_BUCKET environment variable not set")
        return None
    
    try:
        s3_client = get_s3_client()
        
        # List all objects under newsletters/ prefix
        logger.info(f"Listing newsletters from s3://{bucket_name}/newsletters/")
        
        # Use paginator to handle large number of newsletters
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(
            Bucket=bucket_name,
            Prefix='newsletters/'
        )
        
        # Collect all newsletter objects
        all_objects = []
        for page in pages:
            if 'Contents' in page:
                all_objects.extend(page['Contents'])
        
        if not all_objects:
            logger.warning("No newsletters found in S3 archive")
            return None
        
        # Sort by LastModified timestamp (most recent first)
        # The S3 key structure (newsletters/YYYY/MM/DD/) naturally sorts chronologically,
        # but LastModified is more reliable for finding the actual latest newsletter
        sorted_objects = sorted(
            all_objects,
            key=lambda obj: obj['LastModified'],
            reverse=True
        )
        
        # Get the most recent newsletter
        latest_key = sorted_objects[0]['Key']
        logger.info(f"Found latest newsletter: {latest_key}")
        
        # Retrieve the newsletter content
        response = s3_client.get_object(
            Bucket=bucket_name,
            Key=latest_key
        )
        
        # Read and decode the HTML content
        html_content = response['Body'].read().decode('utf-8')
        
        logger.info(f"Successfully retrieved latest newsletter: {latest_key}")
        return html_content
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        logger.error(
            f"Failed to retrieve latest newsletter from S3: "
            f"Code={error_code}, Message={error_msg}"
        )
        return None
        
    except Exception as e:
        logger.error(f"Unexpected error retrieving latest newsletter: {e}")
        return None
