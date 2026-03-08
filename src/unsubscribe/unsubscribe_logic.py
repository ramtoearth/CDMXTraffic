"""
Unsubscribe logic for CDMX Traffic Newsletter

Requirements validated:
- 11.3: Mark subscriber as inactive when unsubscribe link is clicked
- 11.4: Inactive subscribers not included in future distributions
- 11.5: Validate unsubscribe_token before processing
"""
import os
import logging
from typing import Optional, Tuple
import boto3
from botocore.exceptions import ClientError

from src.shared.models import Subscriber

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


def get_subscriber_by_token(unsubscribe_token: str) -> Optional[Subscriber]:
    """
    Scan DynamoDB for subscriber by unsubscribe_token
    
    Args:
        unsubscribe_token: Unique unsubscribe token to search for
        
    Returns:
        Subscriber object if found, None otherwise
        
    Requirements:
        - 11.5: Validate unsubscribe_token before processing
        
    Note: This uses a scan operation which is not ideal for production at scale.
    For better performance, consider adding a GSI on unsubscribe_token.
    """
    table_name = os.environ.get('SUBSCRIBERS_TABLE')
    if not table_name:
        logger.error("SUBSCRIBERS_TABLE environment variable not set")
        return None
    
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table(table_name)
    
    try:
        # Scan for subscriber with matching token
        response = table.scan(
            FilterExpression='unsubscribe_token = :token',
            ExpressionAttributeValues={
                ':token': unsubscribe_token
            }
        )
        
        items = response.get('Items', [])
        if not items:
            logger.warning(f"No subscriber found with token: {unsubscribe_token[:8]}...")
            return None
        
        # Return the first match (should only be one due to uniqueness)
        subscriber = Subscriber.from_dict(items[0])
        logger.info(f"Found subscriber {subscriber.subscriber_id} for token")
        return subscriber
        
    except ClientError as e:
        logger.error(f"Error querying subscriber by token: {e}")
        return None


def update_subscriber_status(subscriber_id: str, active: bool) -> bool:
    """
    Update subscriber's active status in DynamoDB
    
    Args:
        subscriber_id: Unique subscriber ID
        active: New active status (False to deactivate)
        
    Returns:
        True if successful, False otherwise
        
    Requirements:
        - 11.3: Mark subscriber as inactive (active=False)
    """
    table_name = os.environ.get('SUBSCRIBERS_TABLE')
    if not table_name:
        logger.error("SUBSCRIBERS_TABLE environment variable not set")
        return False
    
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table(table_name)
    
    try:
        table.update_item(
            Key={'subscriber_id': subscriber_id},
            UpdateExpression='SET active = :active',
            ExpressionAttributeValues={
                ':active': 'true' if active else 'false'
            }
        )
        logger.info(f"Updated subscriber {subscriber_id} active status to {active}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating subscriber status: {e}")
        return False


def get_subscriber_by_email(email: str) -> Optional[Subscriber]:
    """
    Query DynamoDB for subscriber by email using email-index GSI.

    Returns:
        Subscriber object if found, None otherwise
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
            ExpressionAttributeValues={':email': email}
        )
        items = response.get('Items', [])
        if not items:
            return None
        return Subscriber.from_dict(items[0])
    except ClientError as e:
        logger.error(f"Error querying subscriber by email: {e}")
        return None


def process_unsubscribe_by_email(email: str) -> Tuple[bool, str]:
    """
    Process unsubscribe request using email address.

    Returns:
        Tuple of (success, message)
    """
    email = email.strip().lower()
    if not email:
        return False, "Invalid email address"

    subscriber = get_subscriber_by_email(email)
    if subscriber is None:
        logger.warning(f"No subscriber found for email: {email}")
        return False, "No subscription found for that email address"

    if not subscriber.active:
        return True, "You have already been unsubscribed"

    if update_subscriber_status(subscriber.subscriber_id, active=False):
        logger.info(f"Successfully unsubscribed {email} via email lookup")
        return True, "You have been successfully unsubscribed from the newsletter"
    else:
        return False, "Failed to process unsubscribe request. Please try again later."


def process_unsubscribe(unsubscribe_token: str) -> Tuple[bool, str]:
    """
    Process unsubscribe request by validating token and marking subscriber inactive
    
    Args:
        unsubscribe_token: Unique token from unsubscribe link
        
    Returns:
        Tuple of (success, message)
        - (True, message) if unsubscribe successful
        - (False, error_message) if validation fails or update fails
        
    Requirements:
        - 11.3: Mark subscriber as inactive when unsubscribe link is clicked
        - 11.4: Inactive subscribers not included in future distributions
        - 11.5: Validate unsubscribe_token before processing
        
    Preconditions:
        - unsubscribe_token is non-null and non-empty string
        - DynamoDB table exists and is accessible
        
    Postconditions:
        - If token is valid, subscriber's active field is set to False
        - If token is invalid, returns error message
        - Inactive subscribers will be excluded from future newsletter queries
    """
    # Step 1: Validate token format (basic check)
    if not unsubscribe_token or not isinstance(unsubscribe_token, str):
        logger.warning("Invalid token format: empty or not a string")
        return False, "Invalid unsubscribe token"
    
    token = unsubscribe_token.strip()
    if len(token) < 10:  # UUID should be much longer
        logger.warning(f"Invalid token format: too short ({len(token)} chars)")
        return False, "Invalid unsubscribe token"
    
    # Step 2: Find subscriber by token
    subscriber = get_subscriber_by_token(token)
    if subscriber is None:
        logger.warning(f"Token not found in database: {token[:8]}...")
        return False, "Invalid or expired unsubscribe token"
    
    # Step 3: Check if already inactive
    if not subscriber.active:
        logger.info(f"Subscriber {subscriber.subscriber_id} already inactive")
        return True, "You have already been unsubscribed"
    
    # Step 4: Mark subscriber as inactive
    if update_subscriber_status(subscriber.subscriber_id, active=False):
        logger.info(f"Successfully unsubscribed {subscriber.email}")
        return True, "You have been successfully unsubscribed from the newsletter"
    else:
        logger.error(f"Failed to update subscriber {subscriber.subscriber_id}")
        return False, "Failed to process unsubscribe request. Please try again later."
