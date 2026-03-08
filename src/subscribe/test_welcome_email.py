"""
Tests for welcome email template generation

Requirements validated:
- 2.1, 2.2: Welcome newsletter content
- 11.2: Unsubscribe link with token
"""
import pytest
from src.subscribe.welcome_email import (
    get_welcome_subject,
    generate_welcome_html,
    generate_welcome_text,
)


class TestWelcomeEmailSubject:
    """Test welcome email subject line"""
    
    def test_subject_not_empty(self):
        """Subject should not be empty"""
        subject = get_welcome_subject()
        assert subject
        assert len(subject) > 0
    
    def test_subject_contains_welcome_message(self):
        """Subject should indicate it's a welcome message"""
        subject = get_welcome_subject()
        assert "bienvenido" in subject.lower() or "welcome" in subject.lower()


class TestWelcomeEmailHTML:
    """Test HTML welcome email generation"""
    
    def test_html_contains_greeting_with_name(self):
        """HTML should include personalized greeting when name provided"""
        html = generate_welcome_html(
            name="Juan",
            email="juan@example.com",
            frequency="daily",
            unsubscribe_token="test-token-123",
            landing_url="https://example.com"
        )
        assert "Hola Juan," in html
    
    def test_html_contains_greeting_without_name(self):
        """HTML should include generic greeting when no name provided"""
        html = generate_welcome_html(
            name="",
            email="user@example.com",
            frequency="daily",
            unsubscribe_token="test-token-123",
            landing_url="https://example.com"
        )
        assert "Hola," in html
        assert "Hola ," not in html  # Should not have extra space
    
    def test_html_contains_email_address(self):
        """HTML should display subscriber's email address"""
        email = "subscriber@example.com"
        html = generate_welcome_html(
            name="Test",
            email=email,
            frequency="daily",
            unsubscribe_token="test-token-123",
            landing_url="https://example.com"
        )
        assert email in html
    
    def test_html_contains_frequency_daily(self):
        """HTML should show 'diariamente' for daily frequency"""
        html = generate_welcome_html(
            name="Test",
            email="test@example.com",
            frequency="daily",
            unsubscribe_token="test-token-123",
            landing_url="https://example.com"
        )
        assert "diariamente" in html
    
    def test_html_contains_frequency_weekly(self):
        """HTML should show 'semanalmente' for weekly frequency"""
        html = generate_welcome_html(
            name="Test",
            email="test@example.com",
            frequency="weekly",
            unsubscribe_token="test-token-123",
            landing_url="https://example.com"
        )
        assert "semanalmente" in html
    
    def test_html_contains_unsubscribe_link(self):
        """
        HTML should include unsubscribe link with token
        
        Requirements:
            - 11.2: Include unsubscribe link with token in every newsletter email
        """
        token = "unique-token-456"
        landing_url = "https://example.com"
        html = generate_welcome_html(
            name="Test",
            email="test@example.com",
            frequency="daily",
            unsubscribe_token=token,
            landing_url=landing_url
        )
        expected_url = f"{landing_url}/unsubscribe?token={token}"
        assert expected_url in html
    
    def test_html_contains_landing_page_link(self):
        """HTML should include link to landing page"""
        landing_url = "https://trafico.cdmx.com"
        html = generate_welcome_html(
            name="Test",
            email="test@example.com",
            frequency="daily",
            unsubscribe_token="test-token-123",
            landing_url=landing_url
        )
        assert landing_url in html
    
    def test_html_is_valid_structure(self):
        """HTML should have proper structure"""
        html = generate_welcome_html(
            name="Test",
            email="test@example.com",
            frequency="daily",
            unsubscribe_token="test-token-123",
            landing_url="https://example.com"
        )
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html
        assert "<head>" in html
        assert "</head>" in html
        assert "<body" in html
        assert "</body>" in html
    
    def test_html_contains_expected_content_sections(self):
        """HTML should contain key content sections"""
        html = generate_welcome_html(
            name="Test",
            email="test@example.com",
            frequency="daily",
            unsubscribe_token="test-token-123",
            landing_url="https://example.com"
        )
        # Should mention what subscribers can expect
        assert "esperar" in html.lower()
        # Should mention traffic reports
        assert "tráfico" in html.lower() or "trafico" in html.lower()
        # Should mention incidents
        assert "incidentes" in html.lower()


class TestWelcomeEmailText:
    """Test plain text welcome email generation"""
    
    def test_text_contains_greeting_with_name(self):
        """Text should include personalized greeting when name provided"""
        text = generate_welcome_text(
            name="Maria",
            email="maria@example.com",
            frequency="daily",
            unsubscribe_token="test-token-123",
            landing_url="https://example.com"
        )
        assert "Hola Maria," in text
    
    def test_text_contains_greeting_without_name(self):
        """Text should include generic greeting when no name provided"""
        text = generate_welcome_text(
            name="",
            email="user@example.com",
            frequency="daily",
            unsubscribe_token="test-token-123",
            landing_url="https://example.com"
        )
        assert "Hola," in text
    
    def test_text_contains_email_address(self):
        """Text should display subscriber's email address"""
        email = "subscriber@example.com"
        text = generate_welcome_text(
            name="Test",
            email=email,
            frequency="daily",
            unsubscribe_token="test-token-123",
            landing_url="https://example.com"
        )
        assert email in text
    
    def test_text_contains_frequency_daily(self):
        """Text should show 'diariamente' for daily frequency"""
        text = generate_welcome_text(
            name="Test",
            email="test@example.com",
            frequency="daily",
            unsubscribe_token="test-token-123",
            landing_url="https://example.com"
        )
        assert "diariamente" in text
    
    def test_text_contains_frequency_weekly(self):
        """Text should show 'semanalmente' for weekly frequency"""
        text = generate_welcome_text(
            name="Test",
            email="test@example.com",
            frequency="weekly",
            unsubscribe_token="test-token-123",
            landing_url="https://example.com"
        )
        assert "semanalmente" in text
    
    def test_text_contains_unsubscribe_link(self):
        """
        Text should include unsubscribe link with token
        
        Requirements:
            - 11.2: Include unsubscribe link with token in every newsletter email
        """
        token = "unique-token-789"
        landing_url = "https://example.com"
        text = generate_welcome_text(
            name="Test",
            email="test@example.com",
            frequency="daily",
            unsubscribe_token=token,
            landing_url=landing_url
        )
        expected_url = f"{landing_url}/unsubscribe?token={token}"
        assert expected_url in text
    
    def test_text_contains_landing_page_link(self):
        """Text should include link to landing page"""
        landing_url = "https://trafico.cdmx.com"
        text = generate_welcome_text(
            name="Test",
            email="test@example.com",
            frequency="daily",
            unsubscribe_token="test-token-123",
            landing_url=landing_url
        )
        assert landing_url in text
    
    def test_text_contains_expected_content(self):
        """Text should contain key content sections"""
        text = generate_welcome_text(
            name="Test",
            email="test@example.com",
            frequency="daily",
            unsubscribe_token="test-token-123",
            landing_url="https://example.com"
        )
        # Should mention what subscribers can expect
        assert "esperar" in text.lower()
        # Should mention traffic
        assert "tráfico" in text.lower() or "trafico" in text.lower()
        # Should mention incidents
        assert "incidentes" in text.lower()
    
    def test_text_is_readable_plain_text(self):
        """Text should be plain text without HTML tags"""
        text = generate_welcome_text(
            name="Test",
            email="test@example.com",
            frequency="daily",
            unsubscribe_token="test-token-123",
            landing_url="https://example.com"
        )
        # Should not contain HTML tags
        assert "<html>" not in text
        assert "<body>" not in text
        assert "<div>" not in text
        assert "<p>" not in text
