"""
Data models and validation for subscription functionality
"""
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Subscriber:
    """
    Subscriber data model
    
    Attributes:
        subscriber_id: Unique UUID identifier
        email: Subscriber's email address
        name: Subscriber's name
        frequency: Newsletter frequency ("daily" or "weekly")
        subscribed_at: Timestamp when subscription was created
        last_sent_at: Timestamp of last newsletter sent (None if never sent)
        active: Whether subscription is active
        unsubscribe_token: Unique token for unsubscribe functionality
    """
    subscriber_id: str
    email: str
    name: str
    frequency: str
    subscribed_at: datetime
    last_sent_at: Optional[datetime]
    active: bool
    unsubscribe_token: str


@dataclass
class SubscribeRequest:
    """
    Request model for subscription
    
    Attributes:
        email: User's email address
        frequency: Desired newsletter frequency ("daily" or "weekly")
        name: User's name (optional, defaults to empty string)
    """
    email: str
    frequency: str
    name: str = ""


@dataclass
class SubscribeResponse:
    """
    Response model for subscription requests
    
    Attributes:
        success: Whether the subscription was successful
        message: Human-readable message about the result
        subscriber_id: UUID of the subscriber (None if subscription failed)
    """
    success: bool
    message: str
    subscriber_id: Optional[str] = None


# Email validation regex pattern
# Matches standard email format: local@domain.tld
EMAIL_PATTERN = re.compile(
    r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
)

# Valid frequency options
VALID_FREQUENCIES = ["daily", "weekly"]


def is_valid_email(email: str) -> bool:
    """
    Validates email format using regex pattern
    
    Args:
        email: Email address to validate
        
    Returns:
        True if email matches valid format, False otherwise
        
    Examples:
        >>> is_valid_email("user@example.com")
        True
        >>> is_valid_email("invalid-email")
        False
        >>> is_valid_email("")
        False
        >>> is_valid_email("user@")
        False
    """
    if not email or not isinstance(email, str):
        return False
    
    return EMAIL_PATTERN.match(email) is not None


def validate_frequency(frequency: str) -> bool:
    """
    Validates that frequency is one of the allowed values
    
    Args:
        frequency: Frequency value to validate
        
    Returns:
        True if frequency is "daily" or "weekly", False otherwise
        
    Examples:
        >>> validate_frequency("daily")
        True
        >>> validate_frequency("weekly")
        True
        >>> validate_frequency("monthly")
        False
        >>> validate_frequency("")
        False
    """
    if not frequency or not isinstance(frequency, str):
        return False
    
    return frequency in VALID_FREQUENCIES
