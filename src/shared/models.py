"""
Data models for CDMX Traffic Newsletter

Requirements validated:
- 1.1: Subscriber model with unique subscriber_id
- 1.5: Frequency options (daily/weekly)
- 9.1: Email validation
- 9.2: Frequency validation
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import uuid4


@dataclass
class Subscriber:
    """
    Subscriber model representing a newsletter subscriber
    
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
    active: bool
    unsubscribe_token: str
    last_sent_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for DynamoDB storage"""
        return {
            'subscriber_id': self.subscriber_id,
            'email': self.email,
            'name': self.name,
            'frequency': self.frequency,
            'subscribed_at': self.subscribed_at.isoformat(),
            'last_sent_at': self.last_sent_at.isoformat() if self.last_sent_at else None,
            'active': self.active,
            'unsubscribe_token': self.unsubscribe_token
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Subscriber':
        """Create Subscriber from dictionary (DynamoDB item)"""
        return cls(
            subscriber_id=data['subscriber_id'],
            email=data['email'],
            name=data['name'],
            frequency=data['frequency'],
            subscribed_at=datetime.fromisoformat(data['subscribed_at']),
            last_sent_at=datetime.fromisoformat(data['last_sent_at']) if data.get('last_sent_at') else None,
            active=data['active'],
            unsubscribe_token=data['unsubscribe_token']
        )


@dataclass
class SubscribeRequest:
    """
    Request model for subscription
    
    Attributes:
        email: Email address to subscribe
        frequency: Newsletter frequency ("daily" or "weekly")
        name: Optional subscriber name
    """
    email: str
    frequency: str
    name: str = ""
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SubscribeRequest':
        """Create SubscribeRequest from dictionary"""
        return cls(
            email=data.get('email', ''),
            frequency=data.get('frequency', ''),
            name=data.get('name', '')
        )


@dataclass
class SubscribeResponse:
    """
    Response model for subscription
    
    Attributes:
        success: Whether subscription was successful
        message: Human-readable message
        subscriber_id: UUID of created/updated subscriber (None on failure)
    """
    success: bool
    message: str
    subscriber_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response"""
        result = {
            'success': self.success,
            'message': self.message
        }
        if self.subscriber_id:
            result['subscriber_id'] = self.subscriber_id
        return result


@dataclass
class EmailResponse:
    """
    Response model for email sending operations
    
    Attributes:
        success: Whether email was sent successfully
        message_id: Zavu message ID (None on failure)
        error: Error message (None on success)
    """
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response"""
        result = {
            'success': self.success
        }
        if self.message_id:
            result['message_id'] = self.message_id
        if self.error:
            result['error'] = self.error
        return result
