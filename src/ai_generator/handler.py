"""
AI Generator Lambda Handler
Generates newsletter content using AI (OpenAI) with template-based fallback.

Requirements validated:
- 4.1: Generate HTML and text versions from traffic incidents
- 4.2: Generate relevant subject line
- 4.3: Create executive summary
- 4.4: Extract 3-5 highlights from most important incidents
- 4.5: Handle empty incidents list
- 4.6: Sanitize HTML to prevent XSS
- 4.7: Template-based fallback when AI fails after 3 retries
- 10.4: Log AI generation failures
"""
import json
import logging

from .content_generator import generate_newsletter_with_ai

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Generates newsletter content using AI.

    Expected event:
    {
        "incidents": [
            {
                "type": "accident" | "pothole" | "protest",
                "location": "string",
                "description": "string",
                "severity": "low" | "medium" | "high",
                "timestamp": "ISO string",
                "source": "string"
            },
            ...
        ],
        "date": "YYYY-MM-DD" (optional)
    }

    Returns:
    {
        "html_body": "...",
        "text_body": "...",
        "subject": "...",
        "summary": "...",
        "highlights": ["...", ...]
    }
    """
    logger.info("Starting AI content generation")

    # Parse incidents and date from event
    incidents = event.get("incidents", [])
    target_date = event.get("date")
    
    logger.info(f"Received {len(incidents)} incident(s) for newsletter generation (date={target_date})")

    content = generate_newsletter_with_ai(incidents, target_date=target_date)

    result = {
        "html_body": content.html_body,
        "text_body": content.text_body,
        "subject": content.subject,
        "summary": content.summary,
        "highlights": content.highlights,
    }

    logger.info(
        f"Newsletter generated successfully. "
        f"Subject: '{content.subject}' | Highlights: {len(content.highlights)}"
    )

    return result
