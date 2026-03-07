# Send Email Module

This module handles email sending through the Zavu.dev API with built-in retry logic and rate limiting.

## Components

### `zavu_client.py`
Core client for interacting with Zavu.dev API.

**Key Features:**
- Exponential backoff retry logic (3 attempts)
- Rate limit handling (respects 429 responses)
- Automatic API key retrieval from AWS Secrets Manager
- Comprehensive logging of all attempts and failures

**Main Function:**
```python
def send_email_via_zavu(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str,
    to_name: str = ""
) -> EmailResponse
```

**Requirements Validated:**
- 6.1: Integration with Zavu.dev API
- 6.2: Includes both HTML and text versions
- 6.3: Retry logic with exponential backoff (3 attempts)
- 6.4: Returns message_id on success
- 6.5: Logs failures with error details
- 6.6: Respects rate limits

### `handler.py`
Lambda handler that processes email send requests.

**Expected Event Format:**
```json
{
  "to_email": "user@example.com",
  "to_name": "User Name",
  "subject": "Newsletter Subject",
  "html_body": "<html>...</html>",
  "text_body": "Plain text version...",
  "newsletter_type": "welcome" | "daily"
}
```

**Response Format:**
```json
{
  "success": true,
  "message_id": "msg-123-abc",
  "error": null
}
```

## Configuration

### Environment Variables

The following environment variables are automatically configured via SAM template:

- `ZAVU_API_KEY_SECRET`: ARN/name of the Secrets Manager secret containing the Zavu API key
- `FROM_EMAIL`: Sender email address (default: noreply@cdmxtraffic.com)
- `ZAVU_API_URL`: Zavu API endpoint (default: https://api.zavu.dev/v1/email)
- `AWS_REGION`: AWS region for Secrets Manager (default: us-east-1)

### Secrets Manager

The Zavu API key is stored in AWS Secrets Manager as JSON:
```json
{
  "api_key": "your-zavu-api-key-here"
}
```

Secret name format: `{Environment}/cdmx-traffic/zavu-api-key`

## Retry Logic

The client implements exponential backoff with the following strategy:

1. **Attempt 1**: Immediate send
2. **Attempt 2**: Wait 2 seconds, retry
3. **Attempt 3**: Wait 4 seconds, retry

### Rate Limiting

When Zavu API returns a 429 (rate limit) response:
- The client respects the `Retry-After` header if present
- Falls back to exponential backoff timing if header is missing
- Continues retrying up to the maximum 3 attempts

## Error Handling

The client handles the following error scenarios:

1. **API Key Retrieval Failure**: Returns error immediately without attempting send
2. **Network Timeout**: Retries with exponential backoff
3. **Rate Limiting (429)**: Respects Retry-After header and retries
4. **Server Errors (5xx)**: Retries with exponential backoff
5. **Client Errors (4xx)**: Returns error immediately (except 429)

All errors are logged with full context for debugging.

## Testing

Run the test suite:
```bash
python3 -m pytest src/send_email/test_zavu_client.py -v
```

Tests cover:
- Successful email sending
- API key retrieval from Secrets Manager
- Retry logic on rate limits
- Maximum retry attempts
- Error handling scenarios
- Dual format (HTML + text) validation

## Usage Example

```python
from send_email.zavu_client import send_email_via_zavu

# Send an email
response = send_email_via_zavu(
    to_email="subscriber@example.com",
    subject="🚦 Tu Newsletter Diario de Tráfico CDMX",
    html_body="<html><body><h1>Newsletter</h1></body></html>",
    text_body="Newsletter content in plain text",
    to_name="Juan Pérez"
)

if response.success:
    print(f"Email sent! Message ID: {response.message_id}")
else:
    print(f"Failed to send email: {response.error}")
```

## Lambda Invocation

Invoke the Lambda function directly:
```bash
aws lambda invoke \
  --function-name dev-cdmx-traffic-send-email \
  --payload file://events/send_email.json \
  response.json
```

Example event file (`events/send_email.json`):
```json
{
  "to_email": "test@example.com",
  "to_name": "Test User",
  "subject": "Test Newsletter",
  "html_body": "<p>Test HTML content</p>",
  "text_body": "Test text content",
  "newsletter_type": "welcome"
}
```

## Logging

All operations are logged with the following information:
- Email recipient
- Attempt number
- Success/failure status
- Message ID (on success)
- Error details (on failure)
- Rate limit information

Logs are available in CloudWatch under:
`/aws/lambda/dev-cdmx-traffic-send-email`
