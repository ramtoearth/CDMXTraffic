"""
Zavu.dev API Client
Handles email sending through Zavu.dev with retry logic and rate limiting

Requirements validated:
- 6.1: Integration with Zavu.dev API
- 6.3: Retry logic with exponential backoff (3 attempts)
- 6.6: Rate limit handling
"""
import os
import time
import logging
from typing import Optional
import requests
import boto3
from botocore.exceptions import ClientError

# Import shared models
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from shared.models import EmailResponse

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_zavu_api_key() -> str:
    """
    Retrieve Zavu API key from AWS Secrets Manager
    
    The secret is stored as JSON: {"api_key": "..."}
    
    Returns:
        API key string
        
    Raises:
        Exception: If unable to retrieve secret
    """
    secret_name = os.environ.get('ZAVU_API_KEY_SECRET')
    
    if not secret_name:
        raise Exception("ZAVU_API_KEY_SECRET environment variable not set")
    
    region = os.environ.get('AWS_REGION', 'us-east-1')
    
    try:
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=region
        )
        
        response = client.get_secret_value(SecretId=secret_name)
        
        # Secret is stored as JSON string
        if 'SecretString' in response:
            import json
            secret_dict = json.loads(response['SecretString'])
            return secret_dict.get('api_key', '')
        else:
            raise Exception("Secret is binary, expected string")
            
    except ClientError as e:
        logger.error(f"Failed to retrieve Zavu API key from Secrets Manager: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving Zavu API key: {e}")
        raise


def send_email_via_zavu(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str,
    to_name: str = ""
) -> EmailResponse:
    """
    Send email through Zavu.dev API with retry logic and rate limiting
    
    Implements exponential backoff retry strategy:
    - Attempt 1: immediate
    - Attempt 2: wait 2 seconds
    - Attempt 3: wait 4 seconds
    
    Args:
        to_email: Recipient email address
        subject: Email subject line
        html_body: HTML version of email body
        text_body: Plain text version of email body
        to_name: Optional recipient name
        
    Returns:
        EmailResponse with success status, message_id, or error
        
    Requirements:
        - 6.1: Uses Zavu.dev API
        - 6.2: Includes both HTML and text versions
        - 6.3: Retries up to 3 times with exponential backoff
        - 6.4: Returns message_id on success
        - 6.5: Logs failures with error details
        - 6.6: Respects rate limits
    """
    # Get API key from Secrets Manager
    try:
        api_key = get_zavu_api_key()
    except Exception as e:
        error_msg = f"Failed to retrieve API key: {str(e)}"
        logger.error(error_msg)
        return EmailResponse(success=False, error=error_msg)
    
    # Zavu API endpoint
    api_url = os.environ.get('ZAVU_API_URL', 'https://api.zavu.dev/v1/email')
    from_email = os.environ.get('FROM_EMAIL', 'newsletter@cdmx-traffic.com')
    
    # Prepare request payload
    payload = {
        'from': from_email,
        'to': to_email,
        'subject': subject,
        'html': html_body,
        'text': text_body
    }
    
    if to_name:
        payload['to_name'] = to_name
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    # Retry logic with exponential backoff
    max_attempts = 3
    base_delay = 2  # seconds
    
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"Sending email to {to_email} (attempt {attempt}/{max_attempts})")
            
            response = requests.post(
                api_url,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            # Check for rate limiting (429 status code)
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', base_delay * attempt))
                logger.warning(f"Rate limited by Zavu API. Retry after {retry_after}s")
                
                if attempt < max_attempts:
                    time.sleep(retry_after)
                    continue
                else:
                    error_msg = f"Rate limited after {max_attempts} attempts"
                    logger.error(error_msg)
                    return EmailResponse(success=False, error=error_msg)
            
            # Check for success (2xx status codes)
            if 200 <= response.status_code < 300:
                response_data = response.json()
                message_id = response_data.get('message_id', response_data.get('id'))
                
                logger.info(f"Email sent successfully to {to_email}. Message ID: {message_id}")
                return EmailResponse(success=True, message_id=message_id)
            
            # Handle other error status codes
            error_msg = f"Zavu API error (status {response.status_code}): {response.text}"
            logger.warning(f"Attempt {attempt} failed: {error_msg}")
            
            # If not the last attempt, wait with exponential backoff
            if attempt < max_attempts:
                delay = base_delay * (2 ** (attempt - 1))  # 2, 4, 8 seconds
                logger.info(f"Waiting {delay}s before retry...")
                time.sleep(delay)
            else:
                # Last attempt failed
                logger.error(f"All {max_attempts} attempts failed for {to_email}")
                return EmailResponse(success=False, error=error_msg)
                
        except requests.exceptions.Timeout:
            error_msg = f"Request timeout on attempt {attempt}"
            logger.warning(error_msg)
            
            if attempt < max_attempts:
                delay = base_delay * (2 ** (attempt - 1))
                time.sleep(delay)
            else:
                logger.error(f"Email send failed after {max_attempts} timeout attempts")
                return EmailResponse(success=False, error="Request timeout after all retries")
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error on attempt {attempt}: {str(e)}"
            logger.warning(error_msg)
            
            if attempt < max_attempts:
                delay = base_delay * (2 ** (attempt - 1))
                time.sleep(delay)
            else:
                logger.error(f"Email send failed after {max_attempts} attempts: {str(e)}")
                return EmailResponse(success=False, error=str(e))
                
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            return EmailResponse(success=False, error=error_msg)
    
    # Should not reach here, but just in case
    return EmailResponse(success=False, error="Unknown error after all retry attempts")
