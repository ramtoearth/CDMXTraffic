"""
Unit tests for validation functions

Tests Requirements:
- 1.2: Email format validation
- 1.5: Frequency validation
- 9.1: Email validation using regex
- 9.2: Frequency validation
"""
import pytest
from shared.validation import is_valid_email, validate_frequency, validate_subscribe_request


class TestEmailValidation:
    """Test email validation function"""
    
    def test_valid_emails(self):
        """Test that valid email formats are accepted"""
        valid_emails = [
            "user@example.com",
            "test.user@example.com",
            "user+tag@example.co.uk",
            "user_name@example-domain.com",
            "123@example.com",
            "a@b.co"
        ]
        for email in valid_emails:
            assert is_valid_email(email), f"Expected {email} to be valid"
    
    def test_invalid_emails(self):
        """Test that invalid email formats are rejected"""
        invalid_emails = [
            "",
            "invalid-email",
            "user@",
            "@example.com",
            "user @example.com",
            "user@example",
            "user..name@example.com",
            "user@.example.com",
            "user@example..com",
            None,
            123,
            "a" * 255 + "@example.com"  # Too long
        ]
        for email in invalid_emails:
            assert not is_valid_email(email), f"Expected {email} to be invalid"
    
    def test_email_with_whitespace(self):
        """Test that emails with leading/trailing whitespace are handled"""
        assert is_valid_email("  user@example.com  ")
        assert is_valid_email("\tuser@example.com\n")


class TestFrequencyValidation:
    """Test frequency validation function"""
    
    def test_valid_frequencies(self):
        """Test that valid frequency values are accepted"""
        is_valid, error = validate_frequency("daily")
        assert is_valid
        assert error == ""
        
        is_valid, error = validate_frequency("weekly")
        assert is_valid
        assert error == ""
    
    def test_case_insensitive(self):
        """Test that frequency validation is case-insensitive"""
        for freq in ["DAILY", "Daily", "dAiLy", "WEEKLY", "Weekly", "wEeKlY"]:
            is_valid, error = validate_frequency(freq)
            assert is_valid, f"Expected {freq} to be valid"
            assert error == ""
    
    def test_invalid_frequencies(self):
        """Test that invalid frequency values are rejected"""
        invalid_frequencies = [
            "",
            "monthly",
            "hourly",
            "yearly",
            "invalid",
            None,
            123,
            "daily weekly"
        ]
        for freq in invalid_frequencies:
            is_valid, error = validate_frequency(freq)
            assert not is_valid, f"Expected {freq} to be invalid"
            assert error == "Frequency must be 'daily' or 'weekly'"
    
    def test_frequency_with_whitespace(self):
        """Test that frequencies with leading/trailing whitespace are handled"""
        is_valid, error = validate_frequency("  daily  ")
        assert is_valid
        assert error == ""
        
        is_valid, error = validate_frequency("\tweekly\n")
        assert is_valid
        assert error == ""


class TestSubscribeRequestValidation:
    """Test complete subscription request validation"""
    
    def test_valid_request(self):
        """Test that valid requests pass validation"""
        is_valid, error = validate_subscribe_request("user@example.com", "daily")
        assert is_valid
        assert error == ""
        
        is_valid, error = validate_subscribe_request("test@test.com", "weekly")
        assert is_valid
        assert error == ""
    
    def test_invalid_email_in_request(self):
        """Test that invalid email causes request validation to fail"""
        is_valid, error = validate_subscribe_request("invalid-email", "daily")
        assert not is_valid
        assert error == "Invalid email format"
    
    def test_invalid_frequency_in_request(self):
        """Test that invalid frequency causes request validation to fail"""
        is_valid, error = validate_subscribe_request("user@example.com", "monthly")
        assert not is_valid
        assert error == "Frequency must be 'daily' or 'weekly'"
    
    def test_both_invalid(self):
        """Test that email validation is checked first"""
        is_valid, error = validate_subscribe_request("invalid", "invalid")
        assert not is_valid
        # Email is validated first
        assert error == "Invalid email format"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
