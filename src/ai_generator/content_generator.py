"""
Newsletter content generation with AI, structured extraction, HTML sanitization,
and template-based fallback.

Requirements validated:
- 4.1: Generate HTML and text newsletter from traffic incidents
- 4.2: Generate relevant subject line
- 4.3: Create executive summary
- 4.4: Extract 3-5 highlights from most important incidents
- 4.5: Handle empty incidents list (no-incidents message)
- 4.6: Sanitize HTML to prevent XSS
- 4.7: Template-based fallback when AI fails after 3 retries
- 10.4: Log AI failures
"""
import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
SEVERITY_LABELS = {"high": "Alto", "medium": "Medio", "low": "Bajo"}
INCIDENT_TYPE_LABELS = {
    "accident": "Accidente",
    "pothole": "Bache",
    "protest": "Manifestación",
}

# Patterns for HTML sanitization (Requirement 4.6)
_SCRIPT_RE = re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
_DANGEROUS_TAGS_RE = re.compile(
    r"<(iframe|object|embed|base|form|input|button)[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)
_SELF_CLOSING_DANGEROUS_RE = re.compile(
    r"<(iframe|object|embed|base|input|button)[^>]*/?>",
    re.IGNORECASE,
)
_EVENT_HANDLER_RE = re.compile(r'\s+on\w+="[^"]*"', re.IGNORECASE)
_EVENT_HANDLER_SINGLE_RE = re.compile(r"\s+on\w+='[^']*'", re.IGNORECASE)
_JAVASCRIPT_HREF_RE = re.compile(
    r'(href|src)\s*=\s*["\']?\s*javascript:[^"\'>\s]*["\']?', re.IGNORECASE
)
_DATA_URI_RE = re.compile(
    r'(href|src)\s*=\s*["\']?\s*data:[^"\'>\s]*["\']?', re.IGNORECASE
)


@dataclass
class NewsletterContent:
    """Structured newsletter content returned by the AI generator."""

    html_body: str
    text_body: str
    subject: str
    summary: str
    highlights: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# HTML Sanitization (Requirement 4.6)
# ---------------------------------------------------------------------------


def sanitize_html(html: str) -> str:
    """
    Remove dangerous HTML elements and attributes to prevent XSS.

    Strips:
    - <script> tags and their content
    - <iframe>, <object>, <embed>, <form> tags
    - Event handler attributes (onclick, onload, etc.)
    - javascript: and data: URIs

    Args:
        html: Raw HTML string (possibly AI-generated)

    Returns:
        Sanitized HTML string safe for email delivery
    """
    html = _SCRIPT_RE.sub("", html)
    html = _DANGEROUS_TAGS_RE.sub("", html)
    html = _SELF_CLOSING_DANGEROUS_RE.sub("", html)
    html = _EVENT_HANDLER_RE.sub("", html)
    html = _EVENT_HANDLER_SINGLE_RE.sub("", html)
    html = _JAVASCRIPT_HREF_RE.sub(r'\1="#"', html)
    html = _DATA_URI_RE.sub(r'\1="#"', html)
    return html


# ---------------------------------------------------------------------------
# Incident formatting helpers
# ---------------------------------------------------------------------------


def _sort_incidents_by_severity(incidents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(incidents, key=lambda i: SEVERITY_ORDER.get(i.get("severity", "low"), 2))


def format_incidents_for_prompt(incidents: List[Dict[str, Any]]) -> str:
    """Convert a list of incident dicts to a readable text block for the AI prompt."""
    if not incidents:
        return "No se registraron incidentes hoy."

    lines = []
    for idx, inc in enumerate(_sort_incidents_by_severity(incidents), start=1):
        inc_type = INCIDENT_TYPE_LABELS.get(inc.get("type", ""), inc.get("type", "Incidente"))
        severity = SEVERITY_LABELS.get(inc.get("severity", "low"), inc.get("severity", ""))
        location = inc.get("location", "Ubicación desconocida")
        description = inc.get("description", "")
        source = inc.get("source", "")
        lines.append(
            f"{idx}. [{inc_type} - Severidad {severity}] {location}: {description}"
            + (f" (Fuente: {source})" if source else "")
        )
    return "\n".join(lines)


def extract_highlights(
    incidents: List[Dict[str, Any]], max_count: int = 5
) -> List[str]:
    """
    Extract up to max_count highlights from the most severe incidents.

    Requirement 4.4: Extract 3-5 highlights from the most important incidents.
    """
    sorted_incidents = _sort_incidents_by_severity(incidents)[:max_count]
    highlights = []
    for inc in sorted_incidents:
        inc_type = INCIDENT_TYPE_LABELS.get(inc.get("type", ""), inc.get("type", "Incidente"))
        location = inc.get("location", "Ubicación desconocida")
        description = inc.get("description", "")
        highlights.append(f"{inc_type} en {location}: {description}")
    return highlights if highlights else ["Sin incidentes significativos hoy"]


# ---------------------------------------------------------------------------
# Template-based fallback (Requirement 4.7)
# ---------------------------------------------------------------------------

_FALLBACK_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CDMX Tráfico</title>
</head>
<body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;color:#333;">
  <div style="background-color:#c62828;color:#fff;padding:20px;border-radius:8px 8px 0 0;text-align:center;">
    <h1 style="margin:0;font-size:22px;">CDMX Trafico</h1>
    <p style="margin:5px 0 0 0;font-size:13px;">{date}</p>
  </div>
  <div style="background:#f5f5f5;padding:20px;border:1px solid #ddd;border-top:none;">
    <h2 style="color:#c62828;font-size:16px;margin-top:0;">Resumen</h2>
    <p style="margin:0;">{summary}</p>
  </div>
  <div style="background:#fff;padding:20px;border:1px solid #ddd;border-top:none;">
    <h2 style="color:#c62828;font-size:16px;margin-top:0;">Puntos Clave</h2>
    <ul style="padding-left:20px;margin:0;">
      {highlights_html}
    </ul>
  </div>
  {incidents_section}
  <div style="text-align:center;padding:12px;background:#333;color:#aaa;border-radius:0 0 8px 8px;font-size:11px;">
    <p style="margin:0;">CDMX Traffic Newsletter</p>
  </div>
</body>
</html>"""

_INCIDENT_SECTION_HTML = """\
  <div style="background:#fff;padding:20px;border:1px solid #ddd;border-top:none;">
    <h2 style="color:#c62828;font-size:16px;margin-top:0;">Incidentes del Dia</h2>
    {incidents_html}
  </div>"""

_INCIDENT_ITEM_HTML = """\
    <div style="margin-bottom:12px;padding:10px;background:#fafafa;border-left:4px solid {color};">
      <strong style="font-size:13px;">{type_label} - {location}</strong>
      <p style="margin:4px 0 0 0;font-size:12px;color:#555;">{description}</p>
    </div>"""

_SEVERITY_COLORS = {"high": "#c62828", "medium": "#ef6c00", "low": "#2e7d32"}


def _build_incident_html(incident: Dict[str, Any]) -> str:
    severity = incident.get("severity", "low")
    return _INCIDENT_ITEM_HTML.format(
        color=_SEVERITY_COLORS.get(severity, "#757575"),
        type_label=INCIDENT_TYPE_LABELS.get(incident.get("type", ""), "Incidente"),
        location=incident.get("location", "Ubicación desconocida"),
        description=incident.get("description", ""),
    )


def generate_fallback_content(incidents: List[Dict[str, Any]], target_date: Optional[str] = None) -> NewsletterContent:
    """
    Generate newsletter content using a static template (no AI).

    Used when AI generation fails after all retries.
    Requirement 4.7: Template-based fallback.

    Args:
        incidents: List of traffic incident dicts
        target_date: Optional date string in YYYY-MM-DD format

    Returns:
        NewsletterContent with template-rendered HTML and text
    """
    # Use target_date if provided, otherwise use current date
    if target_date:
        from datetime import datetime as dt
        date_obj = dt.strptime(target_date, "%Y-%m-%d")
        date_str = date_obj.strftime("%d de %B de %Y")
        date_short = date_obj.strftime('%d/%m/%Y')
    else:
        date_str = datetime.now().strftime("%d de %B de %Y")
        date_short = datetime.now().strftime('%d/%m/%Y')
    
    highlights = extract_highlights(incidents, max_count=5)

    if incidents:
        summary = (
            f"Hoy se registraron {len(incidents)} incidente(s) vial(es) en Ciudad de México. "
            "Tome precauciones en las zonas afectadas."
        )
        subject = f"CDMX Trafico {date_short} - {len(incidents)} incidente(s)"
    else:
        summary = (
            "No se registraron incidentes viales significativos en Ciudad de México hoy. "
            "El tráfico fluye con normalidad."
        )
        subject = f"CDMX Trafico {date_short} - Sin incidentes"

    highlights_html = "\n      ".join(
        f'<li style="margin-bottom:6px;font-size:13px;">{h}</li>' for h in highlights
    )

    if incidents:
        sorted_incidents = _sort_incidents_by_severity(incidents)
        incidents_html = "\n".join(_build_incident_html(i) for i in sorted_incidents)
        incidents_section = _INCIDENT_SECTION_HTML.format(incidents_html=incidents_html)
    else:
        incidents_section = ""

    html_body = _FALLBACK_HTML_TEMPLATE.format(
        date=date_str,
        summary=summary,
        highlights_html=highlights_html,
        incidents_section=incidents_section,
    )

    highlights_text = "\n".join(f"- {h}" for h in highlights)
    if incidents:
        incidents_text_lines = []
        for inc in _sort_incidents_by_severity(incidents):
            inc_type = INCIDENT_TYPE_LABELS.get(inc.get("type", ""), "Incidente")
            severity = SEVERITY_LABELS.get(inc.get("severity", "low"), "")
            location = inc.get("location", "")
            description = inc.get("description", "")
            incidents_text_lines.append(
                f"[{inc_type} - {severity}] {location}: {description}"
            )
        incidents_text = "INCIDENTES:\n" + "\n".join(incidents_text_lines)
    else:
        incidents_text = ""

    text_body = (
        f"CDMX TRAFICO - {date_str}\n"
        f"{'=' * 40}\n\n"
        f"RESUMEN:\n{summary}\n\n"
        f"PUNTOS CLAVE:\n{highlights_text}\n\n"
        f"{incidents_text}\n\n"
        "---\nCDMX Traffic Newsletter"
    )

    return NewsletterContent(
        html_body=html_body,
        text_body=text_body,
        subject=subject,
        summary=summary,
        highlights=highlights,
    )


# ---------------------------------------------------------------------------
# AI-powered generation with retry (Requirements 4.1-4.5, 4.7)
# ---------------------------------------------------------------------------


def _parse_ai_response(raw_json: str, incidents: List[Dict[str, Any]]) -> NewsletterContent:
    """
    Parse and validate the JSON response from OpenAI.

    Raises:
        ValueError: If required fields are missing or invalid
    """
    data = json.loads(raw_json)

    subject = str(data.get("subject", "")).strip()
    summary = str(data.get("summary", "")).strip()
    highlights = data.get("highlights", [])
    html_body = str(data.get("html_body", "")).strip()
    text_body = str(data.get("text_body", "")).strip()

    if not subject:
        raise ValueError("Missing 'subject' in AI response")
    if not summary:
        raise ValueError("Missing 'summary' in AI response")
    if not html_body:
        raise ValueError("Missing 'html_body' in AI response")
    if not text_body:
        raise ValueError("Missing 'text_body' in AI response")
    if not isinstance(highlights, list) or len(highlights) == 0:
        # Fallback: extract highlights from incidents instead of failing
        highlights = extract_highlights(incidents, max_count=5)

    # Clamp highlights to 3-5 (Requirement 4.4)
    if len(highlights) > 5:
        highlights = highlights[:5]
    if len(highlights) < 3 and incidents:
        extra = extract_highlights(incidents, max_count=5)
        seen = set(highlights)
        for h in extra:
            if h not in seen and len(highlights) < 3:
                highlights.append(h)
                seen.add(h)

    html_body = sanitize_html(html_body)

    return NewsletterContent(
        html_body=html_body,
        text_body=text_body,
        subject=subject,
        summary=summary,
        highlights=highlights,
    )


def generate_newsletter_with_ai(
    incidents: List[Dict[str, Any]],
    max_retries: int = 3,
    retry_delay: float = 2.0,
    target_date: Optional[str] = None,
) -> NewsletterContent:
    """
    Generate newsletter content using OpenAI, with retry and fallback.

    Attempts AI generation up to max_retries times with exponential backoff.
    Falls back to template-based generation if all attempts fail.

    Args:
        incidents: List of TrafficIncident dicts from the Scraper Lambda
        max_retries: Maximum number of AI call attempts (default 3)
        retry_delay: Base delay in seconds between retries (doubles each attempt)
        target_date: Optional date string in YYYY-MM-DD format

    Returns:
        NewsletterContent with html_body, text_body, subject, summary, highlights

    Requirements:
        - 4.1: Creates HTML and text versions
        - 4.2: Generates subject line
        - 4.3: Creates executive summary
        - 4.4: Extracts 3-5 highlights
        - 4.5: Handles empty incidents list
        - 4.7: Falls back to template if AI fails after retries
        - 10.4: Logs AI failures
    """
    from .openai_client import (  # noqa: PLC0415
        NEWSLETTER_PROMPT_TEMPLATE,
        NO_INCIDENTS_PROMPT,
        call_openai_api,
    )

    # Build prompt (Requirement 4.5: handle empty incidents)
    if incidents:
        incidents_text = format_incidents_for_prompt(incidents)
        prompt = NEWSLETTER_PROMPT_TEMPLATE.format(incidents_text=incidents_text)
    else:
        prompt = NO_INCIDENTS_PROMPT

    last_error: Optional[Exception] = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"AI generation attempt {attempt}/{max_retries}")
            raw_response = call_openai_api(prompt)
            content = _parse_ai_response(raw_response, incidents)
            logger.info(f"AI newsletter generation succeeded on attempt {attempt}")
            return content

        except Exception as e:
            last_error = e
            logger.warning(
                f"AI generation attempt {attempt}/{max_retries} failed: {e}"
            )
            if attempt < max_retries:
                delay = retry_delay * (2 ** (attempt - 1))
                logger.info(f"Retrying in {delay:.1f}s...")
                time.sleep(delay)

    # All retries exhausted — use fallback (Requirement 4.7, 10.4)
    logger.error(
        f"AI generation failed after {max_retries} attempts. "
        f"Last error: {last_error}. Using template fallback."
    )
    return generate_fallback_content(incidents, target_date=target_date)
