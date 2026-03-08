# Generate Newsletter Lambda

## Overview

The Generate Newsletter Lambda is the main orchestrator for the daily newsletter generation and distribution process. It coordinates multiple Lambda functions to:

1. **Scrape traffic data** - Invokes the Scraper Lambda to collect current traffic incidents
2. **Generate content** - Invokes the AI Generator Lambda to create newsletter content
3. **Archive newsletter** - Saves the newsletter to S3 (task 7.2)
4. **Distribute to subscribers** - Sends emails to all active daily subscribers (task 7.3)

## Architecture

```
EventBridge (7 AM daily)
    ↓
Generate Newsletter Lambda (Orchestrator)
    ↓
    ├─→ Scraper Lambda → Traffic Data
    ├─→ AI Generator Lambda → Newsletter Content
    ├─→ S3 → Archive Newsletter
    └─→ Send Email Lambda (for each subscriber)
```

## Implementation Status

### ✅ Task 7.1 - Main Orchestration Function (COMPLETED)

Implemented `generate_and_send_daily_newsletter()` function that:
- Invokes Scraper Lambda to collect traffic incidents
- Invokes AI Generator Lambda to create newsletter content
- Returns structured result with metrics

**Files:**
- `orchestrator.py` - Core orchestration logic
- `handler.py` - Lambda handler entry point
- `test_orchestrator.py` - Unit tests for orchestration
- `test_handler.py` - Unit tests for handler

**Environment Variables:**
- `SCRAPER_FUNCTION_NAME` - Name of the Scraper Lambda function
- `AI_GENERATOR_FUNCTION_NAME` - Name of the AI Generator Lambda function
- `SEND_EMAIL_FUNCTION_NAME` - Name of the Send Email Lambda function (for task 7.3)
- `SUBSCRIBERS_TABLE` - DynamoDB table name (for task 7.3)
- `NEWSLETTER_BUCKET` - S3 bucket name (for task 7.2)

### 🔄 Task 7.2 - S3 Archiving (TODO)

Will implement:
- `archive_newsletter_to_s3()` function
- Generate unique newsletter_id
- Save HTML content to S3 with proper key format

### 🔄 Task 7.3 - Subscriber Distribution (TODO)

Will implement:
- `get_active_subscribers_by_frequency()` function
- Loop through subscribers and invoke Send Email Lambda
- Update `last_sent_at` timestamp for each subscriber
- Log metrics (sent_count, failed_count)

## Lambda Invocation

### Scraper Lambda

**Invocation:**
```python
response = lambda_client.invoke(
    FunctionName=scraper_function_name,
    InvocationType='RequestResponse',
    Payload=json.dumps({})
)
```

**Response:**
```json
{
    "statusCode": 200,
    "body": {
        "incidents": [...],
        "scraped_at": "2024-01-15T10:00:00",
        "sources_count": 2,
        "incidents_count": 5
    }
}
```

### AI Generator Lambda

**Invocation:**
```python
response = lambda_client.invoke(
    FunctionName=ai_generator_function_name,
    InvocationType='RequestResponse',
    Payload=json.dumps({
        "incidents": [...]
    })
)
```

**Response:**
```json
{
    "html_body": "<html>...</html>",
    "text_body": "...",
    "subject": "Traffic Update - Jan 15",
    "summary": "...",
    "highlights": ["...", "..."]
}
```

## Testing

Run unit tests:
```bash
python3 -m pytest src/generate_newsletter/ -v
```

Run specific test file:
```bash
python3 -m pytest src/generate_newsletter/test_orchestrator.py -v
```

## Requirements Validated

- **5.2**: WHEN the daily trigger executes, THE System SHALL scrape current traffic data
- **5.3**: WHEN traffic data is collected, THE System SHALL generate newsletter content using AI

## Error Handling

The orchestrator implements proper error handling:
- Validates environment variables are set
- Checks Lambda invocation status codes
- Validates response payloads have required fields
- Propagates errors with descriptive messages
- Logs all operations for debugging

## Future Enhancements

1. **Retry Logic**: Add retry logic for Lambda invocations
2. **Circuit Breaker**: Implement circuit breaker pattern for external services
3. **Metrics**: Add CloudWatch custom metrics for monitoring
4. **Parallel Processing**: Process subscribers in parallel batches
5. **Dead Letter Queue**: Add DLQ for failed newsletter generations
