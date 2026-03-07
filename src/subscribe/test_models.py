"""
Unit tests for subscription models and validation
"""
import pytest
from datetime import datetime
from src.subscribe.models import (
    Subscriber,
    SubscribeRequest,
    SubscribeResponse,
    is_valid_email,
    validate_frequency,
    VALID_FREQUENCIES
)


class TestSubscriber:
    """Tests for Subscriber dataclass"""
    
    def test_subscriber_creation(self):
        """Test creating a Subscriber instance"""
        subscriber = Subscriber(
            subscriber_id="123e4567-e89b-12d3-a456-426614174000",
            email="test@example.com",
            name="Test User",
            frequency="daily",
            subscribed_at=datetime.now(),
            last_sent_at=None,
            active=True,
            unsubscribe_token="abc123"
        )
        
        assert subscriber.subscriber_id == "123e4567-e89b-12d3-a456-426614174000"
        assert subscriber.email == "test@example.com"
        assert subscriber.name == "Test User"
        assert subscriber.frequency == "daily"
        assert subscriber.active is True
        assert subscriber.last_sent_at is None


class TestSubscribeRequest:
    """Tests for SubscribeRequest dataclass"""
    
    def test_subscribe_request_with_name(self):
        """Test creating SubscribeRequest with name"""
        request = SubscribeRequest(
            email="user@example.com",
            frequency="weekly",
            name="John Doe"
        )
        
        assert request.email == "user@example.com"
        assert request.frequency == "weekly"
        assert request.name == "John Doe"
    
    def test_subscribe_request_without_name(self):
        """Test creating SubscribeRequest without name (defaults to empty string)"""
        request = SubscribeRequest(
            email="user@example.com",
            frequency="daily"
        )
        
        assert request.email == "user@example.com"
        assert request.frequency == "daily"
        assert request.name == ""


class TestSubscribeResponse:
    """Tests for SubscribeResponse dataclass"""
    
    def test_subscribe_response_success(self):
        """Test successful subscription response"""
        response = SubscribeResponse(
            success=True,
            message="Subscription successful",
            subscriber_id="123e4567-e89b-12d3-a456-426614174000"
        )
        
        assert response.success is True
        assert response.message == "Subscription successful"
        assert response.subscriber_id == "123e4567-e89b-12d3-a456-426614174000"
    
    def test_subscribe_response_failure(self):
        """Test failed subscription response"""
        response = SubscribeResponse(
            success=False,
            message="Invalid email format"
        )
        
        assert response.success is False
        assert response.message == "Invalid email format"
        assert response.subscriber_id is None


class TestIsValidEmail:
    """Tests for is_valid_email validation function"""
    
    def test_valid_emails(self):
        """Test that valid email formats are accepted"""
        valid_emails = [
            "user@example.com",
            "test.user@example.com",
            "user+tag@example.co.uk",
            "user_name@example-domain.com",
            "123@example.com",
            "user@subdomain.example.com"
        ]
        
        for email in valid_emails:
            assert is_valid_email(email) is True, f"Expected {email} to be valid"
    
    def test_invalid_emails(self):
        """Test that invalid email formats are rejected"""
        invalid_emails = [
            "invalid-email",
            "user@",
            "@example.com",
            "user @example.com",
            "user@example",
            "",
            "user@.com",
            "user..name@example.com",
            "user@example..com"
        ]
        
        for email in invalid_emails:
            assert is_valid_email(email) is False, f"Expected {email} to be invalid"
    
    def test_empty_string(self):
        """Test that empty string is invalid"""
        assert is_valid_email("") is False
    
    def test_none_value(self):
        """Test that None is invalid"""
        assert is_valid_email(None) is False
    
    def test_non_string_value(self):
        """Test that non-string values are invalid"""
        assert is_valid_email(123) is False
        assert is_valid_email([]) is False
        assert is_valid_email({}) is False


class TestValidateFrequency:
    """Tests for validate_frequency validation function"""
    
    def test_valid_frequencies(self):
        """Test that valid frequency values are accepted"""
        for frequency in VALID_FREQUENCIES:
            assert validate_frequency(frequency) is True, f"Expected {frequency} to be valid"
    
    def test_daily_frequency(self):
        """Test that 'daily' is valid"""
        assert validate_frequency("daily") is True
    
    def test_weekly_frequency(self):
        """Test that 'weekly' is valid"""
        assert validate_frequency("weekly") is True
    
    def test_invalid_frequencies(self):
        """Test that invalid frequency values are rejected"""
        invalid_frequencies = [
            "monthly",
            "yearly",
            "hourly",
            "Daily",  # Case sensitive
            "WEEKLY",  # Case sensitive
            "biweekly",
            ""
        ]
        
        for frequency in invalid_frequencies:
            assert validate_frequency(frequency) is False, f"Expected {frequency} to be invalid"
    
    def test_empty_string(self):
        """Test that empty string is invalid"""
        assert validate_frequency("") is False
    
    def test_none_value(self):
        """Test that None is invalid"""
        assert validate_frequency(None) is False
    
    def test_non_string_value(self):
        """Test that non-string values are invalid"""
        assert validate_frequency(123) is False
        assert validate_frequency([]) is False
        assert validate_frequency({}) is False
