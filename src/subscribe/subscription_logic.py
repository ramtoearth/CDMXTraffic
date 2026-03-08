"""
Subscription logic for CDMX Traffic Newsletter

Requirements validated:
- 1.1: Create subscriber with unique subscriber_id
- 1.3: Handle duplicate email subscriptions
- 1.4: Reactivate previously unsubscribed emails
- 11.1: Generate unique unsubscribe_token
"""
import json
import os
import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4
import boto3
from botocore.exceptions import ClientError

from src.shared.models import Subscriber, SubscribeResponse
from src.shared.validation import validate_subscribe_request
from src.subscribe.welcome_email import (
    generate_welcome_html,
    generate_welcome_text,
    get_welcome_subject,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# DynamoDB resource will be initialized lazily
_dynamodb = None


def get_dynamodb_resource():
    """Get or create DynamoDB resource (lazy initialization)"""
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource('dynamodb')
    return _dynamodb


def get_subscriber_by_email(email: str) -> Optional[Subscriber]:
    """
    Query DynamoDB for subscriber by email using email-index GSI
    
    Args:
        email: Email address to search for
        
    Returns:
        Subscriber object if found, None otherwise
        
    Requirements:
        - 1.3: Check for existing subscribers by email
    """
    table_name = os.environ.get('SUBSCRIBERS_TABLE')
    if not table_name:
        logger.error("SUBSCRIBERS_TABLE environment variable not set")
        return None
    
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table(table_name)
    
    try:
        response = table.query(
            IndexName='email-index',
            KeyConditionExpression='email = :email',
            ExpressionAttributeValues={
                ':email': email
            }
        )
        
        items = response.get('Items', [])
        if not items:
            return None
        
        # Return the first match (should only be one due to uniqueness)
        return Subscriber.from_dict(items[0])
        
    except ClientError as e:
        logger.error(f"Error querying subscriber by email: {e}")
        return None


def save_subscriber_to_db(subscriber: Subscriber) -> bool:
    """
    Save subscriber to DynamoDB
    
    Args:
        subscriber: Subscriber object to save
        
    Returns:
        True if successful, False otherwise
        
    Requirements:
        - 1.1: Save subscriber to DynamoDB
    """
    table_name = os.environ.get('SUBSCRIBERS_TABLE')
    if not table_name:
        logger.error("SUBSCRIBERS_TABLE environment variable not set")
        return False
    
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table(table_name)
    
    try:
        table.put_item(Item=subscriber.to_dict())
        logger.info(f"Saved subscriber {subscriber.subscriber_id} to DynamoDB")
        return True
        
    except ClientError as e:
        logger.error(f"Error saving subscriber to DynamoDB: {e}")
        return False


def send_welcome_email(subscriber: Subscriber) -> None:
    """
    Invoke the send-email Lambda with a welcome email for the subscriber.
    Never raises — email failure must not affect subscription outcome.
    """
    function_name = os.environ.get('SEND_EMAIL_FUNCTION_NAME')
    landing_url = os.environ.get('LANDING_PAGE_URL', '')

    if not function_name:
        logger.warning("SEND_EMAIL_FUNCTION_NAME not set; skipping welcome email")
        return

    try:
        html_body = generate_welcome_html(
            name=subscriber.name,
            email=subscriber.email,
            frequency=subscriber.frequency,
            unsubscribe_token=subscriber.unsubscribe_token,
            landing_url=landing_url,
        )
        text_body = generate_welcome_text(
            name=subscriber.name,
            email=subscriber.email,
            frequency=subscriber.frequency,
            unsubscribe_token=subscriber.unsubscribe_token,
            landing_url=landing_url,
        )
        payload = {
            'to_email': subscriber.email,
            'to_name': subscriber.name,
            'subject': get_welcome_subject(),
            'html_body': html_body,
            'text_body': text_body,
            'newsletter_type': 'welcome',
        }
        client = boto3.client('lambda')
        response = client.invoke(
            FunctionName=function_name,
            InvocationType='Event',
            Payload=json.dumps(payload).encode(),
        )
        logger.info(
            f"Welcome email dispatched for {subscriber.email}; "
            f"StatusCode={response.get('StatusCode')}"
        )
    except Exception as e:
        logger.error(f"Failed to send welcome email to {subscriber.email}: {e}")


def generate_unsubscribe_token() -> str:
    """
    Generate unique unsubscribe token using UUID4
    
    Returns:
        Unique token string
        
    Requirements:
        - 11.1: Generate unique unsubscribe_token
    """
    return str(uuid4())


def validate_and_save_subscriber(
    email: str,
    frequency: str,
    name: str = ""
) -> SubscribeResponse:
    """
    Validates and saves a new subscriber to DynamoDB
    
    Handles:
    - Email format validation
    - Frequency validation
    - Duplicate email detection
    - Subscription reactivation
    - Unique token generation
    
    Args:
        email: Email address to subscribe
        frequency: Newsletter frequency ("daily" or "weekly")
        name: Optional subscriber name
        
    Returns:
        SubscribeResponse with success status and message
        
    Requirements:
        - 1.1: Create new subscriber record with unique subscriber_id
        - 1.3: Return error if email already subscribed and active
        - 1.4: Reactivate subscription if email exists but inactive
        - 11.1: Generate unique unsubscribe_token
        
    Preconditions:
        - email is non-null and non-empty string
        - frequency is either "daily" or "weekly"
        - DynamoDB table exists and is accessible
        
    Postconditions:
        - Returns SubscribeResponse with success=True if subscriber saved
        - Subscriber record exists in DynamoDB with unique subscriber_id
        - If email already exists and active, returns success=False with appropriate message
        - unsubscribe_token is generated and stored
    """
    # Step 1: Validate email and frequency
    is_valid, error_msg = validate_subscribe_request(email, frequency)
    if not is_valid:
        logger.warning(f"Validation failed for {email}: {error_msg}")
        return SubscribeResponse(
            success=False,
            message=error_msg
        )
    
    # Normalize email and frequency
    email = email.strip().lower()
    frequency = frequency.strip().lower()
    
    # Step 2: Check if email already exists
    existing_subscriber = get_subscriber_by_email(email)
    
    if existing_subscriber is not None:
        if existing_subscriber.active:
            # Email already subscribed and active
            logger.info(f"Email {email} already subscribed and active")
            return SubscribeResponse(
                success=False,
                message="Email already subscribed"
            )
        else:
            # Reactivate subscription with new frequency
            logger.info(f"Reactivating subscription for {email}")
            existing_subscriber.active = True
            existing_subscriber.frequency = frequency
            existing_subscriber.name = name if name else existing_subscriber.name
            existing_subscriber.subscribed_at = datetime.now()
            
            # Save updated subscriber
            if save_subscriber_to_db(existing_subscriber):
                send_welcome_email(existing_subscriber)
                return SubscribeResponse(
                    success=True,
                    message="Subscription reactivated",
                    subscriber_id=existing_subscriber.subscriber_id
                )
            else:
                return SubscribeResponse(
                    success=False,
                    message="Failed to reactivate subscription"
                )
    
    # Step 3: Create new subscriber
    subscriber_id = str(uuid4())
    unsubscribe_token = generate_unsubscribe_token()
    
    subscriber = Subscriber(
        subscriber_id=subscriber_id,
        email=email,
        name=name,
        frequency=frequency,
        subscribed_at=datetime.now(),
        last_sent_at=None,
        active=True,
        unsubscribe_token=unsubscribe_token
    )
    
    # Step 4: Save to DynamoDB
    if save_subscriber_to_db(subscriber):
        logger.info(f"Successfully created new subscriber {subscriber_id}")
        send_welcome_email(subscriber)
        return SubscribeResponse(
            success=True,
            message="Subscription successful",
            subscriber_id=subscriber_id
        )
    else:
        logger.error(f"Failed to save subscriber {subscriber_id} to database")
        return SubscribeResponse(
            success=False,
            message="Failed to save subscription"
        )
