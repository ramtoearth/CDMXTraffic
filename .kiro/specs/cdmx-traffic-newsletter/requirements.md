# Requirements Document

## Introduction

Sistema automatizado de newsletter que recopila información sobre incidentes viales en Ciudad de México mediante web scraping e IA, y envía newsletters personalizadas a suscriptores a través de Zavu.dev. El sistema incluye una landing page con ejemplos de newsletters anteriores y envía automáticamente un newsletter de bienvenida al suscribirse, además de envíos programados diarios a las 7 AM.

## Glossary

- **System**: El sistema completo de newsletter de tráfico CDMX
- **Subscriber**: Usuario que se ha suscrito para recibir newsletters
- **Newsletter**: Email con información sobre incidentes viales
- **Incident**: Evento vial (accidente, bache, manifestación)
- **Scraper**: Componente que recopila datos de fuentes externas
- **AI_Generator**: Componente que genera contenido usando IA
- **Email_Service**: Servicio de envío de emails (Zavu.dev)
- **Landing_Page**: Página web de suscripción
- **Archive**: Almacenamiento de newsletters en S3

## Requirements

### Requirement 1: User Subscription

**User Story:** As a user, I want to subscribe to the newsletter with my email and preferred frequency, so that I receive traffic updates according to my preferences.

#### Acceptance Criteria

1. WHEN a user submits a valid email and frequency, THE System SHALL create a new subscriber record with a unique subscriber_id
2. WHEN a user submits an invalid email format, THE System SHALL reject the subscription and return an error message
3. WHEN a user attempts to subscribe with an already active email, THE System SHALL return an error message indicating the email is already subscribed
4. WHEN a user subscribes with a previously unsubscribed email, THE System SHALL reactivate the subscription with the new frequency preference
5. THE System SHALL support two frequency options: "daily" and "weekly"

### Requirement 2: Welcome Newsletter

**User Story:** As a new subscriber, I want to receive a welcome newsletter immediately after subscribing, so that I can confirm my subscription and see what to expect.

#### Acceptance Criteria

1. WHEN a new subscriber is successfully created, THE System SHALL send a welcome newsletter to the subscriber's email
2. WHEN a subscription is reactivated, THE System SHALL send a welcome newsletter to the subscriber's email
3. THE System SHALL mark the welcome newsletter with type "welcome" for tracking purposes
4. IF the welcome email fails to send, THEN THE System SHALL log the failure but maintain the subscription as active

### Requirement 3: Traffic Data Collection

**User Story:** As the system, I want to scrape traffic data from multiple sources, so that I can provide comprehensive and up-to-date information to subscribers.

#### Acceptance Criteria

1. THE Scraper SHALL collect traffic incidents from multiple configured data sources
2. WHEN scraping a source, THE Scraper SHALL normalize data into a standard TrafficIncident format
3. THE Scraper SHALL classify each incident by type: "accident", "pothole", or "protest"
4. THE Scraper SHALL assign severity levels: "low", "medium", or "high" to each incident
5. WHEN a data source is unavailable, THE Scraper SHALL continue with remaining sources and log the failure
6. THE Scraper SHALL remove duplicate incidents based on location and timestamp proximity
7. IF all data sources fail, THEN THE System SHALL generate a newsletter indicating no data is available

### Requirement 4: AI Content Generation

**User Story:** As the system, I want to generate engaging newsletter content using AI, so that subscribers receive well-formatted and readable traffic updates.

#### Acceptance Criteria

1. WHEN traffic incidents are provided, THE AI_Generator SHALL create newsletter content with HTML and text versions
2. THE AI_Generator SHALL generate a relevant subject line for the newsletter
3. THE AI_Generator SHALL create an executive summary of the traffic situation
4. THE AI_Generator SHALL extract 3-5 highlights from the most important incidents
5. WHEN no incidents are available, THE AI_Generator SHALL generate a "no incidents today" message
6. THE AI_Generator SHALL ensure HTML content is properly formatted and sanitized
7. IF the AI service fails after 3 retries, THEN THE System SHALL use a template-based fallback for content generation

### Requirement 5: Daily Newsletter Distribution

**User Story:** As a daily subscriber, I want to receive a newsletter every day at 7 AM, so that I can plan my commute with current traffic information.

#### Acceptance Criteria

1. THE System SHALL trigger newsletter generation daily at 7:00 AM Mexico City time
2. WHEN the daily trigger executes, THE System SHALL scrape current traffic data
3. WHEN traffic data is collected, THE System SHALL generate newsletter content using AI
4. WHEN newsletter content is generated, THE System SHALL archive it to S3 with a unique newsletter_id
5. THE System SHALL retrieve all active subscribers with frequency "daily"
6. WHEN subscribers are retrieved, THE System SHALL send the newsletter to each daily subscriber
7. WHEN a newsletter is sent successfully, THE System SHALL update the subscriber's last_sent_at timestamp
8. THE System SHALL log the count of successful and failed email deliveries

### Requirement 6: Email Delivery

**User Story:** As the system, I want to reliably send emails through Zavu.dev, so that subscribers receive their newsletters.

#### Acceptance Criteria

1. WHEN sending an email, THE Email_Service SHALL use the Zavu.dev API
2. THE Email_Service SHALL include both HTML and text versions in each email
3. WHEN an email send fails, THE Email_Service SHALL retry up to 3 times with exponential backoff
4. WHEN an email send succeeds, THE Email_Service SHALL return the message_id from Zavu
5. IF an email fails after all retries, THEN THE Email_Service SHALL log the failure with error details
6. THE Email_Service SHALL respect Zavu API rate limits

### Requirement 7: Newsletter Archive

**User Story:** As the system, I want to archive all generated newsletters, so that they can be displayed on the landing page and for historical reference.

#### Acceptance Criteria

1. WHEN a newsletter is generated, THE System SHALL save the HTML content to S3
2. THE System SHALL use the S3 key format: newsletters/YYYY/MM/DD/{newsletter_id}.html
3. WHEN archiving fails after 3 retries, THE System SHALL log the error but continue with email distribution
4. THE Archive SHALL store newsletters with public-read permissions for landing page access

### Requirement 8: Landing Page Sample Display

**User Story:** As a potential subscriber, I want to see an example of a previous newsletter on the landing page, so that I can decide if I want to subscribe.

#### Acceptance Criteria

1. WHEN a user visits the landing page, THE System SHALL provide an endpoint to retrieve a sample newsletter
2. THE System SHALL return the most recent newsletter from the S3 archive
3. THE System SHALL include CORS headers to allow landing page access
4. THE System SHALL return HTML content with appropriate Content-Type header

### Requirement 9: Data Validation

**User Story:** As the system, I want to validate all data inputs and outputs, so that data integrity is maintained throughout the system.

#### Acceptance Criteria

1. THE System SHALL validate that subscriber emails match a valid email format pattern
2. THE System SHALL validate that frequency values are either "daily" or "weekly"
3. THE System SHALL validate that incident types are one of: "accident", "pothole", "protest"
4. THE System SHALL validate that severity levels are one of: "low", "medium", "high"
5. THE System SHALL ensure all TrafficIncident objects have non-empty location and description fields
6. THE System SHALL ensure all Newsletter objects have non-empty html_body and text_body fields

### Requirement 10: Error Handling and Logging

**User Story:** As a system administrator, I want comprehensive error logging, so that I can monitor system health and troubleshoot issues.

#### Acceptance Criteria

1. WHEN any component encounters an error, THE System SHALL log the error with timestamp, component name, and error details
2. WHEN a data source fails to scrape, THE System SHALL log the source URL and error message
3. WHEN an email fails to send, THE System SHALL log the subscriber_id and failure reason
4. WHEN the AI service fails, THE System SHALL log the failure and indicate fallback usage
5. THE System SHALL log execution metrics for each newsletter generation including sent_count, failed_count, and incidents_count
6. IF a critical service fails 3 consecutive times, THEN THE System SHALL send an alert to monitoring

### Requirement 11: Subscriber Management

**User Story:** As a subscriber, I want to be able to unsubscribe from the newsletter, so that I can stop receiving emails when I no longer need them.

#### Acceptance Criteria

1. WHEN a subscriber is created, THE System SHALL generate a unique unsubscribe_token
2. THE System SHALL include an unsubscribe link with the token in every newsletter email
3. WHEN a user clicks the unsubscribe link, THE System SHALL mark the subscriber as inactive (active=False)
4. WHEN a subscriber is marked inactive, THE System SHALL not include them in future newsletter distributions
5. THE System SHALL validate the unsubscribe_token before processing unsubscribe requests

### Requirement 12: Performance and Scalability

**User Story:** As the system, I want to process newsletters efficiently, so that all subscribers receive timely emails.

#### Acceptance Criteria

1. THE System SHALL complete subscriber subscription requests in less than 1 second
2. THE Scraper SHALL complete data collection from all sources within 30 seconds
3. THE AI_Generator SHALL generate newsletter content within 15 seconds
4. THE Email_Service SHALL send individual emails within 3 seconds each
5. THE System SHALL process subscribers in batches of 50 for concurrent email sending
6. WHEN the subscriber count exceeds 1000, THE System SHALL use concurrent Lambda invocations for email distribution
