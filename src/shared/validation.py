"""
Validation functions for CDMX Traffic Newsletter

Requirements validated:
- 1.2: Email format validation
- 1.5: Frequency validation
- 9.1: Email validation using regex pattern
- 9.2: Frequency must be "daily" or "weekly"
"""
import re
from typing import Tuple


# Email validation regex pattern (RFC 5322 simplified)
EMAIL_PATTERN = re.compile(
    r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
)

# Valid frequency options
VALID_FREQUENCIES = {"daily", "weekly"}


def is_valid_email(email: str) -> bool:
    """
    Validate email format using regex pattern
    
    Args:
        email: Email address to validate
        
    Returns:
        True if email matches valid format, False otherwise
        
    Requirements:
        - 1.2: Email format validation
        - 9.1: Email validation using regex pattern
        
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
    
    # Strip whitespace
    email = email.strip()
    
    # Check length constraints
    if len(email) < 3 or len(email) > 254:
        return False
    
    # Match against regex pattern
    return bool(EMAIL_PATTERN.match(email))


def validate_frequency(frequency: str) -> Tuple[bool, str]:
    """
    Validate frequency value
    
    Args:
        frequency: Frequency value to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        - (True, "") if valid
        - (False, error_message) if invalid
        
    Requirements:
        - 1.5: Frequency must be "daily" or "weekly"
        - 9.2: Frequency validation
        
    Examples:
        >>> validate_frequency("daily")
        (True, "")
        >>> validate_frequency("weekly")
        (True, "")
        >>> validate_frequency("monthly")
        (False, "Frequency must be 'daily' or 'weekly'")
        >>> validate_frequency("")
        (False, "Frequency must be 'daily' or 'weekly'")
    """
    if not frequency or not isinstance(frequency, str):
        return False, "Frequency must be 'daily' or 'weekly'"
    
    # Normalize to lowercase
    frequency = frequency.strip().lower()
    
    if frequency not in VALID_FREQUENCIES:
        return False, "Frequency must be 'daily' or 'weekly'"
    
    return True, ""


def validate_subscribe_request(email: str, frequency: str) -> Tuple[bool, str]:
    """
    Validate complete subscription request
    
    Args:
        email: Email address
        frequency: Newsletter frequency
        
    Returns:
        Tuple of (is_valid, error_message)
        - (True, "") if all validations pass
        - (False, error_message) if any validation fails
        
    Requirements:
        - 1.2: Email format validation
        - 1.5: Frequency validation
        - 9.1: Email validation
        - 9.2: Frequency validation
    """
    # Validate email
    if not is_valid_email(email):
        return False, "Invalid email format"
    
    # Validate frequency
    is_valid, error_msg = validate_frequency(frequency)
    if not is_valid:
        return False, error_msg
    
    return True, ""
