"""
Verification test for Task 8.1: Welcome Newsletter Template

This test verifies that the welcome newsletter template meets all requirements:
- 2.1: Send welcome newsletter to new subscribers
- 2.2: Send welcome newsletter on reactivation
- 11.2: Include unsubscribe link with token

Run with: python3 test_task_8_1_verification.py
"""
from src.subscribe.welcome_email import (
    get_welcome_subject,
    generate_welcome_html,
    generate_welcome_text,
)


def test_welcome_newsletter_template():
    """Verify welcome newsletter template meets all requirements"""
    
    print("=" * 70)
    print("TASK 8.1 VERIFICATION: Welcome Newsletter Template")
    print("=" * 70)
    
    # Test data
    test_name = "Juan Pérez"
    test_email = "juan.perez@example.com"
    test_frequency = "daily"
    test_token = "abc123-def456-ghi789"
    test_landing_url = "https://trafico.cdmx.com"
    
    print("\n1. Testing Subject Line...")
    subject = get_welcome_subject()
    print(f"   Subject: {subject}")
    assert subject, "Subject should not be empty"
    assert len(subject) > 0, "Subject should have content"
    print("   ✓ Subject line is valid")
    
    print("\n2. Testing HTML Template...")
    html = generate_welcome_html(
        name=test_name,
        email=test_email,
        frequency=test_frequency,
        unsubscribe_token=test_token,
        landing_url=test_landing_url
    )
    
    # Requirement 2.1, 2.2: Welcome newsletter content
    print("   Checking welcome message...")
    assert "suscrito exitosamente" in html.lower(), "Should contain subscription confirmation"
    print("   ✓ Contains welcome message")
    
    print("   Checking personalization...")
    assert test_name in html, "Should include subscriber name"
    assert test_email in html, "Should include subscriber email"
    print("   ✓ Contains personalized information")
    
    print("   Checking frequency information...")
    assert "diariamente" in html, "Should show daily frequency"
    print("   ✓ Contains frequency information")
    
    # Requirement 11.2: Include unsubscribe link with token
    print("   Checking unsubscribe link...")
    expected_unsubscribe_url = f"{test_landing_url}/unsubscribe?token={test_token}"
    assert expected_unsubscribe_url in html, "Should include unsubscribe link with token"
    print(f"   ✓ Contains unsubscribe link: {expected_unsubscribe_url}")
    
    print("   Checking HTML structure...")
    assert "<!DOCTYPE html>" in html, "Should have DOCTYPE"
    assert "<html" in html and "</html>" in html, "Should have html tags"
    assert "<head>" in html and "</head>" in html, "Should have head section"
    assert "<body" in html and "</body>" in html, "Should have body section"
    print("   ✓ HTML structure is valid")
    
    print("   Checking content sections...")
    assert "esperar" in html.lower(), "Should explain what to expect"
    assert "incidentes" in html.lower(), "Should mention incidents"
    assert "tráfico" in html.lower() or "trafico" in html.lower(), "Should mention traffic"
    print("   ✓ Contains all expected content sections")
    
    print("\n3. Testing Plain Text Template...")
    text = generate_welcome_text(
        name=test_name,
        email=test_email,
        frequency=test_frequency,
        unsubscribe_token=test_token,
        landing_url=test_landing_url
    )
    
    print("   Checking text content...")
    assert test_name in text, "Should include subscriber name"
    assert test_email in text, "Should include subscriber email"
    assert "diariamente" in text, "Should show daily frequency"
    print("   ✓ Contains personalized information")
    
    # Requirement 11.2: Include unsubscribe link with token
    print("   Checking unsubscribe link in text...")
    assert expected_unsubscribe_url in text, "Should include unsubscribe link with token"
    print("   ✓ Contains unsubscribe link")
    
    print("   Checking plain text format...")
    assert "<html>" not in text, "Should not contain HTML tags"
    assert "<body>" not in text, "Should not contain HTML tags"
    assert "<div>" not in text, "Should not contain HTML tags"
    print("   ✓ Plain text format is correct")
    
    print("\n4. Testing Weekly Frequency...")
    html_weekly = generate_welcome_html(
        name=test_name,
        email=test_email,
        frequency="weekly",
        unsubscribe_token=test_token,
        landing_url=test_landing_url
    )
    assert "semanalmente" in html_weekly, "Should show weekly frequency"
    print("   ✓ Weekly frequency is handled correctly")
    
    print("\n5. Testing Without Name...")
    html_no_name = generate_welcome_html(
        name="",
        email=test_email,
        frequency=test_frequency,
        unsubscribe_token=test_token,
        landing_url=test_landing_url
    )
    assert "Hola," in html_no_name, "Should have generic greeting"
    assert "Hola ," not in html_no_name, "Should not have extra space"
    print("   ✓ Handles missing name gracefully")
    
    print("\n" + "=" * 70)
    print("✅ ALL VERIFICATION TESTS PASSED!")
    print("=" * 70)
    print("\nRequirements Validated:")
    print("  ✓ 2.1: Welcome newsletter content for new subscribers")
    print("  ✓ 2.2: Welcome newsletter content for reactivated subscribers")
    print("  ✓ 11.2: Unsubscribe link with token included in newsletter")
    print("\nTask 8.1 is COMPLETE!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        test_welcome_newsletter_template()
    except AssertionError as e:
        print(f"\n❌ VERIFICATION FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        exit(1)
