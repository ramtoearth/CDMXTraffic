"""
Newsletter Generation Orchestrator

Orchestrates the daily newsletter generation process by coordinating:
- Scraper Lambda (traffic data collection)
- AI Generator Lambda (content generation)
- S3 archiving
- Email distribution to subscribers

Requirements validated:
- 5.2: Scrape current traffic data when daily trigger executes
- 5.3: Generate newsletter content using AI when traffic data is collected
- 5.4: Archive newsletter to S3 with unique newsletter_id
- 5.5: Retrieve all active subscribers with frequency "daily"
- 5.6: Send newsletter to each daily subscriber
- 5.7: Update subscriber's last_sent_at timestamp when newsletter sent successfully
- 7.1: Save HTML content to S3 when newsletter is generated
- 7.2: Use S3 key format newsletters/YYYY/MM/DD/{newsletter_id}.html
- 7.3: Continue with email distribution if archiving fails after retries
- 10.5: Log execution metrics including sent_count, failed_count, incidents_count
"""
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import uuid4
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients will be initialized lazily
_lambda_client = None
_s3_client = None


def get_lambda_client():
    """Get or create Lambda client (lazy initialization)"""
    global _lambda_client
    if _lambda_client is None:
        _lambda_client = boto3.client('lambda')
    return _lambda_client


def get_s3_client():
    """Get or create S3 client (lazy initialization)"""
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client('s3')
    return _s3_client

def get_dynamodb_resource():
    """Get or create DynamoDB resource (lazy initialization)"""
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource('dynamodb')
    return _dynamodb


# AWS clients will be initialized lazily
_dynamodb = None



def invoke_scraper_lambda() -> Dict[str, Any]:
    """
    Invokes the Scraper Lambda to collect traffic data
    
    Returns:
        Dictionary containing:
        - incidents: List of traffic incident dictionaries
        - scraped_at: ISO timestamp
        - sources_count: Number of sources attempted
        - incidents_count: Number of incidents returned
        
    Raises:
        Exception: If Lambda invocation fails
        
    Requirements:
        - 5.2: Scrape current traffic data when daily trigger executes
    """
    scraper_function_name = os.environ.get('SCRAPER_FUNCTION_NAME')
    if not scraper_function_name:
        logger.error("SCRAPER_FUNCTION_NAME environment variable not set")
        raise ValueError("SCRAPER_FUNCTION_NAME not configured")
    
    logger.info(f"Invoking Scraper Lambda: {scraper_function_name}")
    
    try:
        lambda_client = get_lambda_client()
        
        # Invoke Scraper Lambda synchronously
        response = lambda_client.invoke(
            FunctionName=scraper_function_name,
            InvocationType='RequestResponse',  # Synchronous invocation
            Payload=json.dumps({})  # Scraper doesn't need input parameters
        )
        
        # Parse response
        status_code = response['StatusCode']
        if status_code != 200:
            logger.error(f"Scraper Lambda returned status code {status_code}")
            raise Exception(f"Scraper Lambda invocation failed with status {status_code}")
        
        # Read and parse payload
        payload = json.loads(response['Payload'].read())
        
        # Check if Lambda execution was successful
        if payload.get('statusCode') != 200:
            error_msg = payload.get('body', 'Unknown error')
            logger.error(f"Scraper Lambda execution failed: {error_msg}")
            raise Exception(f"Scraper Lambda execution failed: {error_msg}")
        
        # Parse body (it's a JSON string)
        body = json.loads(payload['body'])
        
        incidents_count = body.get('incidents_count', 0)
        sources_count = body.get('sources_count', 0)
        
        logger.info(
            f"Scraper Lambda completed successfully: "
            f"{incidents_count} incidents from {sources_count} sources"
        )
        
        return body
        
    except ClientError as e:
        logger.error(f"AWS error invoking Scraper Lambda: {e}")
        raise
    except Exception as e:
        logger.error(f"Error invoking Scraper Lambda: {e}")
        raise


def invoke_ai_generator_lambda(incidents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Invokes the AI Generator Lambda to create newsletter content
    
    Args:
        incidents: List of traffic incident dictionaries
        
    Returns:
        Dictionary containing:
        - html_body: HTML version of newsletter
        - text_body: Plain text version of newsletter
        - subject: Email subject line
        - summary: Executive summary
        - highlights: List of 3-5 key highlights
        
    Raises:
        Exception: If Lambda invocation fails
        
    Requirements:
        - 5.3: Generate newsletter content using AI when traffic data is collected
    """
    ai_generator_function_name = os.environ.get('AI_GENERATOR_FUNCTION_NAME')
    if not ai_generator_function_name:
        logger.error("AI_GENERATOR_FUNCTION_NAME environment variable not set")
        raise ValueError("AI_GENERATOR_FUNCTION_NAME not configured")
    
    logger.info(
        f"Invoking AI Generator Lambda: {ai_generator_function_name} "
        f"with {len(incidents)} incidents"
    )
    
    try:
        lambda_client = get_lambda_client()
        
        # Prepare payload with incidents
        payload = {
            'incidents': incidents
        }
        
        # Invoke AI Generator Lambda synchronously
        response = lambda_client.invoke(
            FunctionName=ai_generator_function_name,
            InvocationType='RequestResponse',  # Synchronous invocation
            Payload=json.dumps(payload)
        )
        
        # Parse response
        status_code = response['StatusCode']
        if status_code != 200:
            logger.error(f"AI Generator Lambda returned status code {status_code}")
            raise Exception(f"AI Generator Lambda invocation failed with status {status_code}")
        
        # Read and parse payload
        content = json.loads(response['Payload'].read())
        
        # Validate response has required fields
        required_fields = ['html_body', 'text_body', 'subject', 'summary', 'highlights']
        for field in required_fields:
            if field not in content:
                logger.error(f"AI Generator response missing required field: {field}")
                raise Exception(f"Invalid AI Generator response: missing {field}")
        
        logger.info(
            f"AI Generator Lambda completed successfully: "
            f"Subject='{content['subject']}', Highlights={len(content['highlights'])}"
        )
        
        return content
        
    except ClientError as e:
        logger.error(f"AWS error invoking AI Generator Lambda: {e}")
        raise
    except Exception as e:
        logger.error(f"Error invoking AI Generator Lambda: {e}")
        raise


def archive_newsletter_to_s3(
    html_content: str,
    newsletter_id: Optional[str] = None,
    created_at: Optional[datetime] = None
) -> Optional[str]:
    """
    Archives newsletter HTML content to S3 with proper key format
    
    Args:
        html_content: HTML content of the newsletter
        newsletter_id: Optional newsletter ID (generates UUID if not provided)
        created_at: Optional timestamp (uses current time if not provided)
        
    Returns:
        newsletter_id if successful, None if archiving fails after retries
        
    Requirements:
        - 5.4: Archive newsletter to S3 with unique newsletter_id
        - 7.1: Save HTML content to S3 when newsletter is generated
        - 7.2: Use S3 key format newsletters/YYYY/MM/DD/{newsletter_id}.html
        - 7.3: Continue with email distribution if archiving fails after retries
        
    Preconditions:
        - html_content is non-empty string
        - NEWSLETTER_BUCKET environment variable is set
        - S3 bucket exists and is accessible
        
    Postconditions:
        - If successful: Newsletter is stored in S3 with correct key format
        - If failed: Error is logged but function returns None (doesn't raise)
        - newsletter_id is returned on success, None on failure
    """
    bucket_name = os.environ.get('NEWSLETTER_BUCKET')
    if not bucket_name:
        logger.error("NEWSLETTER_BUCKET environment variable not set")
        return None
    
    # Generate newsletter_id if not provided
    if newsletter_id is None:
        newsletter_id = str(uuid4())
    
    # Use current time if not provided
    if created_at is None:
        created_at = datetime.now()
    
    # Format S3 key: newsletters/YYYY/MM/DD/{newsletter_id}.html
    s3_key = f"newsletters/{created_at.strftime('%Y/%m/%d')}/{newsletter_id}.html"
    
    logger.info(f"Archiving newsletter to S3: s3://{bucket_name}/{s3_key}")
    
    # Retry logic: 3 attempts with exponential backoff
    max_retries = 3
    retry_delay = 1  # Start with 1 second
    
    for attempt in range(1, max_retries + 1):
        try:
            s3_client = get_s3_client()
            
            # Upload to S3 with public-read ACL for landing page access
            s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=html_content.encode('utf-8'),
                ContentType='text/html',
                ACL='public-read'
            )
            
            logger.info(
                f"Successfully archived newsletter to S3: {newsletter_id} "
                f"(attempt {attempt}/{max_retries})"
            )
            
            return newsletter_id
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_msg = e.response.get('Error', {}).get('Message', str(e))
            
            logger.error(
                f"S3 archiving failed (attempt {attempt}/{max_retries}): "
                f"Code={error_code}, Message={error_msg}"
            )
            
            # If this was the last attempt, log and return None
            if attempt == max_retries:
                logger.error(
                    f"S3 archiving failed after {max_retries} retries. "
                    f"Continuing with email distribution. Newsletter ID: {newsletter_id}"
                )
                return None
            
            # Wait before retrying (exponential backoff)
            time.sleep(retry_delay)
            retry_delay *= 2  # Double the delay for next retry
            
        except Exception as e:
            logger.error(
                f"Unexpected error archiving to S3 (attempt {attempt}/{max_retries}): {e}"
            )
            
            # If this was the last attempt, log and return None
            if attempt == max_retries:
                logger.error(
                    f"S3 archiving failed after {max_retries} retries due to unexpected error. "
                    f"Continuing with email distribution. Newsletter ID: {newsletter_id}"
                )
                return None
            
            # Wait before retrying
            time.sleep(retry_delay)
            retry_delay *= 2
    
    # Should never reach here, but return None as safety
    return None

def get_active_subscribers_by_frequency(frequency: str) -> List[Dict[str, Any]]:
    """
    Retrieves active subscribers for given frequency from DynamoDB

    Args:
        frequency: Newsletter frequency ("daily" or "weekly")

    Returns:
        List of subscriber dictionaries where active=True and frequency matches
        Empty list if no subscribers match or on error

    Requirements:
        - 5.5: Retrieve all active subscribers with frequency "daily"

    Preconditions:
        - frequency is "daily" or "weekly"
        - DynamoDB table exists and is accessible
        - GSI on frequency+active exists

    Postconditions:
        - Returns list of subscriber dicts where active=True and frequency matches
        - Empty list returned if no subscribers match
        - All returned subscribers have valid email addresses
    """
    table_name = os.environ.get('SUBSCRIBERS_TABLE')
    if not table_name:
        logger.error("SUBSCRIBERS_TABLE environment variable not set")
        return []

    logger.info(f"Querying active subscribers with frequency: {frequency}")

    try:
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(table_name)

        # Query using frequency-active-index GSI
        # The GSI has frequency as partition key and active as sort key
        response = table.query(
            IndexName='frequency-active-index',
            KeyConditionExpression='frequency = :freq AND active = :active',
            ExpressionAttributeValues={
                ':freq': frequency,
                ':active': 'true'
            }
        )

        subscribers = response.get('Items', [])

        # Handle pagination if there are more results
        while 'LastEvaluatedKey' in response:
            response = table.query(
                IndexName='frequency-active-index',
                KeyConditionExpression='frequency = :freq AND active = :active',
                ExpressionAttributeValues={
                    ':freq': frequency,
                    ':active': 'true'
                },
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            subscribers.extend(response.get('Items', []))

        logger.info(f"Found {len(subscribers)} active {frequency} subscribers")

        return subscribers

    except ClientError as e:
        logger.error(f"Error querying subscribers by frequency: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error querying subscribers: {e}")
        return []


def update_subscriber_last_sent(subscriber_id: str) -> bool:
    """
    Updates the last_sent_at timestamp for a subscriber

    Args:
        subscriber_id: Unique subscriber ID

    Returns:
        True if update successful, False otherwise

    Requirements:
        - 5.7: Update subscriber's last_sent_at timestamp when newsletter sent successfully
    """
    table_name = os.environ.get('SUBSCRIBERS_TABLE')
    if not table_name:
        logger.error("SUBSCRIBERS_TABLE environment variable not set")
        return False

    try:
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(table_name)

        # Update last_sent_at timestamp
        table.update_item(
            Key={'subscriber_id': subscriber_id},
            UpdateExpression='SET last_sent_at = :timestamp',
            ExpressionAttributeValues={
                ':timestamp': datetime.now().isoformat()
            }
        )

        return True

    except ClientError as e:
        logger.error(f"Error updating last_sent_at for subscriber {subscriber_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error updating subscriber: {e}")
        return False


def invoke_send_email_lambda(
    to_email: str,
    to_name: str,
    subject: str,
    html_body: str,
    text_body: str,
    newsletter_type: str = "daily"
) -> Dict[str, Any]:
    """
    Invokes the Send Email Lambda to send a newsletter

    Args:
        to_email: Recipient email address
        to_name: Recipient name
        subject: Email subject line
        html_body: HTML version of email
        text_body: Plain text version of email
        newsletter_type: Type of newsletter ("daily" or "welcome")

    Returns:
        Dictionary with 'success' boolean and optional 'message_id' or 'error'

    Requirements:
        - 5.6: Send newsletter to each daily subscriber
    """
    send_email_function_name = os.environ.get('SEND_EMAIL_FUNCTION_NAME')
    if not send_email_function_name:
        logger.error("SEND_EMAIL_FUNCTION_NAME environment variable not set")
        return {'success': False, 'error': 'SEND_EMAIL_FUNCTION_NAME not configured'}

    try:
        lambda_client = get_lambda_client()

        # Prepare payload
        payload = {
            'to_email': to_email,
            'to_name': to_name,
            'subject': subject,
            'html_body': html_body,
            'text_body': text_body,
            'newsletter_type': newsletter_type
        }

        # Invoke Send Email Lambda synchronously
        response = lambda_client.invoke(
            FunctionName=send_email_function_name,
            InvocationType='RequestResponse',  # Synchronous invocation
            Payload=json.dumps(payload)
        )

        # Parse response
        status_code = response['StatusCode']
        if status_code != 200:
            logger.error(f"Send Email Lambda returned status code {status_code}")
            return {'success': False, 'error': f'Lambda invocation failed with status {status_code}'}

        # Read and parse payload
        result = json.loads(response['Payload'].read())

        # Parse body (it's a JSON string)
        body = json.loads(result.get('body', '{}'))

        return body

    except ClientError as e:
        logger.error(f"AWS error invoking Send Email Lambda: {e}")
        return {'success': False, 'error': str(e)}
    except Exception as e:
        logger.error(f"Error invoking Send Email Lambda: {e}")
        return {'success': False, 'error': str(e)}


def log_newsletter_metrics(
    newsletter_id: str,
    sent_count: int,
    failed_count: int,
    incidents_count: int
) -> None:
    """
    Logs execution metrics for newsletter generation

    Args:
        newsletter_id: Unique newsletter identifier
        sent_count: Number of emails successfully sent
        failed_count: Number of emails that failed
        incidents_count: Number of traffic incidents processed

    Requirements:
        - 10.5: Log execution metrics including sent_count, failed_count, incidents_count
    """
    logger.info(
        f"Newsletter Metrics - "
        f"newsletter_id={newsletter_id}, "
        f"sent_count={sent_count}, "
        f"failed_count={failed_count}, "
        f"incidents_count={incidents_count}, "
        f"total_subscribers={sent_count + failed_count}"
    )



def generate_and_send_daily_newsletter() -> Dict[str, Any]:
    """
    Main orchestration function for daily newsletter generation and distribution
    
    Orchestrates the complete newsletter workflow:
    1. Invoke Scraper Lambda to collect traffic data
    2. Invoke AI Generator Lambda to create newsletter content
    3. Archive newsletter to S3
    4. Query active daily subscribers
    5. Send emails to all subscribers
    6. Log execution metrics
    
    Returns:
        Dictionary containing:
        - newsletter_id: Unique identifier for this newsletter
        - sent_count: Number of emails successfully sent
        - failed_count: Number of emails that failed
        - incidents_count: Number of traffic incidents processed
        - subject: Newsletter subject line
        - highlights_count: Number of highlights generated
        
    Requirements:
        - 5.2: Scrape current traffic data when daily trigger executes
        - 5.3: Generate newsletter content using AI when traffic data is collected
        - 5.4: Archive newsletter to S3 with unique newsletter_id
        - 5.5: Retrieve all active subscribers with frequency "daily"
        - 5.6: Send newsletter to each daily subscriber
        - 5.7: Update subscriber's last_sent_at timestamp when newsletter sent successfully
        - 10.5: Log execution metrics including sent_count, failed_count, incidents_count
        
    Preconditions:
        - All Lambda functions are deployed and accessible
        - DynamoDB table has active subscribers
        - Environment variables are configured
        - External data sources are available
        
    Postconditions:
        - Newsletter is generated and archived in S3
        - All daily subscribers receive the newsletter
        - Execution metrics are logged
        - Subscriber last_sent_at timestamps are updated
    """
    logger.info("Starting daily newsletter generation orchestration")
    
    try:
        # Step 1: Scrape traffic data
        logger.info("Step 1: Invoking Scraper Lambda")
        scraper_response = invoke_scraper_lambda()
        
        incidents = scraper_response.get('incidents', [])
        incidents_count = len(incidents)
        sources_count = scraper_response.get('sources_count', 0)
        
        logger.info(
            f"Scraping completed: {incidents_count} incidents from {sources_count} sources"
        )
        
        # Step 2: Generate newsletter content with AI
        logger.info("Step 2: Invoking AI Generator Lambda")
        content = invoke_ai_generator_lambda(incidents)
        
        logger.info(
            f"Newsletter content generated: Subject='{content['subject']}'"
        )
        
        # Step 3: Archive newsletter in S3
        logger.info("Step 3: Archiving newsletter to S3")
        newsletter_id = archive_newsletter_to_s3(content['html_body'])
        
        # If archiving failed, generate a fallback ID but continue
        if newsletter_id is None:
            newsletter_id = str(uuid4())
            logger.warning(
                f"S3 archiving failed, using fallback newsletter_id: {newsletter_id}"
            )
        else:
            logger.info(f"Newsletter archived successfully: {newsletter_id}")
        
        # Step 4: Get active daily subscribers
        logger.info("Step 4: Querying active daily subscribers")
        subscribers = get_active_subscribers_by_frequency("daily")
        
        logger.info(f"Found {len(subscribers)} active daily subscribers")
        
        # Step 5: Send emails to all subscribers
        logger.info("Step 5: Sending newsletters to subscribers")
        sent_count = 0
        failed_count = 0
        
        for subscriber in subscribers:
            subscriber_id = subscriber.get('subscriber_id')
            email = subscriber.get('email')
            name = subscriber.get('name', '')
            
            logger.info(f"Sending newsletter to {email} (subscriber_id: {subscriber_id})")
            
            # Invoke Send Email Lambda
            email_response = invoke_send_email_lambda(
                to_email=email,
                to_name=name,
                subject=content['subject'],
                html_body=content['html_body'],
                text_body=content['text_body'],
                newsletter_type='daily'
            )
            
            # Check if email was sent successfully
            if email_response.get('success'):
                sent_count += 1
                # Update last_sent_at timestamp
                if update_subscriber_last_sent(subscriber_id):
                    logger.info(f"Successfully sent newsletter to {email}")
                else:
                    logger.warning(
                        f"Email sent to {email} but failed to update last_sent_at"
                    )
            else:
                failed_count += 1
                error = email_response.get('error', 'Unknown error')
                logger.error(
                    f"Failed to send newsletter to {email}: {error}"
                )
        
        # Step 6: Log execution metrics
        log_newsletter_metrics(newsletter_id, sent_count, failed_count, incidents_count)
        
        result = {
            'newsletter_id': newsletter_id,
            'sent_count': sent_count,
            'failed_count': failed_count,
            'incidents_count': incidents_count,
            'subject': content['subject'],
            'highlights_count': len(content['highlights'])
        }
        
        logger.info(
            f"Newsletter orchestration completed: "
            f"{incidents_count} incidents processed, "
            f"{sent_count} emails sent, {failed_count} failed"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error in newsletter orchestration: {e}")
        raise

