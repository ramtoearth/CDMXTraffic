# Implementation Plan: CDMX Traffic Newsletter

## Overview

Sistema serverless en AWS que automatiza la recopilación de información de tráfico en CDMX mediante web scraping e IA, y envía newsletters personalizadas a suscriptores. Arquitectura basada en AWS Lambda, DynamoDB, S3, API Gateway y EventBridge, con integración a Zavu.dev para envío de emails. Implementación enfocada en MVP funcional para vibe racing de 1 hora.

## Tasks

- [x] 1. Configurar infraestructura base con SAM
  - Crear template.yaml con recursos básicos: DynamoDB table, S3 bucket, API Gateway
  - Configurar variables de entorno y Secrets Manager para API keys
  - Definir IAM roles y políticas para Lambdas
  - _Requirements: 12.1, 12.2_

- [ ] 2. Implementar Subscribe Lambda y API endpoint
  - [x] 2.1 Crear modelos de datos y validación
    - Implementar dataclasses: Subscriber, SubscribeRequest, SubscribeResponse
    - Crear funciones de validación: is_valid_email(), validate_frequency()
    - _Requirements: 1.1, 1.2, 1.5, 9.1, 9.2_
  
  - [ ]* 2.2 Escribir property test para validación de email
    - **Property 2: Email Format Validation**
    - **Validates: Requirements 1.2, 9.1**
  
  - [x] 2.3 Implementar lógica de suscripción
    - Crear función validate_and_save_subscriber() con manejo de duplicados
    - Implementar generación de unsubscribe_token único
    - Integrar con DynamoDB para guardar suscriptores
    - _Requirements: 1.1, 1.3, 1.4, 11.1_
  
  - [ ]* 2.4 Escribir property test para unicidad de email
    - **Property 3: Email Uniqueness**
    - **Validates: Requirements 1.3**
  
  - [x] 2.5 Crear Lambda handler para POST /subscribe
    - Implementar lambda_handler con parsing de request
    - Agregar manejo de errores y respuestas HTTP
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [ ] 3. Implementar Send Email Lambda con integración Zavu.dev
  - [x] 3.1 Crear cliente de Zavu.dev API
    - Implementar send_email_via_zavu() con retry logic
    - Configurar exponential backoff (3 intentos)
    - Manejar rate limits de Zavu API
    - _Requirements: 6.1, 6.3, 6.6_
  
  - [ ]* 3.2 Escribir property test para retry logic
    - **Property 22: Email Retry Logic**
    - **Validates: Requirements 6.3**
  
  - [-] 3.3 Implementar Lambda handler para envío de emails
    - Crear lambda_handler que procesa EmailRequest
    - Incluir HTML y texto plano en cada email
    - Agregar logging de éxitos y fallos
    - _Requirements: 6.1, 6.2, 6.4, 6.5, 10.3_

- [~] 4. Checkpoint - Validar suscripción y envío básico
  - Probar flujo de suscripción end-to-end
  - Verificar que emails se envían correctamente vía Zavu
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implementar Scraper Lambda para recopilación de datos
  - [~] 5.1 Crear estructura de TrafficIncident y funciones de scraping
    - Implementar dataclass TrafficIncident con validaciones
    - Crear scrape_traffic_sources() con manejo de múltiples fuentes
    - Implementar parsers para cada fuente de datos
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 9.3, 9.4, 9.5_
  
  - [~] 5.2 Implementar deduplicación de incidentes
    - Crear deduplicate_incidents() basado en location y timestamp
    - Implementar create_incident_fingerprint() para identificación única
    - _Requirements: 3.6_
  
  - [ ]* 5.3 Escribir property test para deduplicación
    - **Property 13: Incident Deduplication**
    - **Validates: Requirements 3.6**
  
  - [~] 5.4 Agregar resiliencia y manejo de errores
    - Implementar manejo de fuentes no disponibles
    - Agregar logging de errores por fuente
    - Continuar con fuentes restantes si una falla
    - _Requirements: 3.5, 10.2_

- [ ] 6. Implementar AI Content Generator Lambda
  - [~] 6.1 Crear integración con OpenAI/Bedrock
    - Implementar generate_newsletter_with_ai() con llamada a LLM
    - Crear prompt template para generación de newsletter
    - Manejar caso de lista vacía de incidentes
    - _Requirements: 4.1, 4.2, 4.3, 4.5_
  
  - [~] 6.2 Implementar generación de contenido estructurado
    - Extraer highlights (3-5 items) de incidentes
    - Crear executive summary
    - Generar HTML y texto plano
    - Sanitizar HTML para prevenir XSS
    - _Requirements: 4.4, 4.6_
  
  - [ ]* 6.3 Escribir property test para completitud de contenido
    - **Property 14: Newsletter Content Completeness**
    - **Validates: Requirements 4.1, 4.2, 4.3, 9.6**
  
  - [~] 6.4 Agregar fallback template-based
    - Crear template simple para cuando AI falla
    - Implementar retry logic (3 intentos)
    - _Requirements: 4.7, 10.4_

- [ ] 7. Implementar Generate Newsletter Lambda (orquestador)
  - [~] 7.1 Crear función principal de orquestación
    - Implementar generate_and_send_daily_newsletter()
    - Invocar Scraper Lambda para obtener datos
    - Invocar AI Generator Lambda para crear contenido
    - _Requirements: 5.2, 5.3_
  
  - [~] 7.2 Implementar archivado en S3
    - Crear función archive_newsletter_to_s3() con formato de key correcto
    - Manejar fallos de S3 sin bloquear distribución
    - _Requirements: 5.4, 7.1, 7.2, 7.3_
  
  - [~] 7.3 Implementar consulta y envío a suscriptores
    - Crear get_active_subscribers_by_frequency("daily")
    - Implementar loop de envío con actualización de last_sent_at
    - Agregar logging de métricas (sent_count, failed_count)
    - _Requirements: 5.5, 5.6, 5.7, 10.5_
  
  - [ ]* 7.4 Escribir property test para filtrado de suscriptores
    - **Property 18: Daily Subscriber Filtering**
    - **Validates: Requirements 5.5**
  
  - [~] 7.5 Configurar EventBridge para trigger diario a las 7 AM
    - Agregar regla de EventBridge en template.yaml
    - Configurar timezone de Ciudad de México
    - _Requirements: 5.1_

- [ ] 8. Implementar welcome newsletter en Subscribe Lambda
  - [~] 8.1 Crear contenido de welcome newsletter
    - Diseñar template HTML para email de bienvenida
    - Incluir link de unsubscribe con token
    - _Requirements: 2.1, 2.2, 11.2_
  
  - [~] 8.2 Integrar envío de welcome email en flujo de suscripción
    - Triggear Send Email Lambda después de guardar suscriptor
    - Manejar fallos sin afectar la suscripción
    - _Requirements: 2.1, 2.2, 2.3, 2.4_
  
  - [ ]* 8.3 Escribir property test para welcome newsletter
    - **Property 6: Welcome Newsletter on New Subscription**
    - **Validates: Requirements 2.1, 2.3**

- [~] 9. Checkpoint - Validar generación y envío de newsletter
  - Probar generación completa de newsletter con datos reales
  - Verificar archivado en S3
  - Verificar envío a múltiples suscriptores
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Implementar Get Sample Newsletter Lambda y endpoint
  - [~] 10.1 Crear función para obtener último newsletter de S3
    - Implementar get_latest_newsletter_from_s3()
    - Ordenar por timestamp para obtener el más reciente
    - _Requirements: 8.2_
  
  - [~] 10.2 Crear Lambda handler para GET /sample-newsletter
    - Implementar lambda_handler con headers CORS
    - Configurar Content-Type: text/html
    - _Requirements: 8.1, 8.3, 8.4_

- [ ] 11. Implementar funcionalidad de unsubscribe
  - [~] 11.1 Crear endpoint POST /unsubscribe
    - Validar unsubscribe_token
    - Marcar subscriber como inactive (active=False)
    - Agregar rate limiting
    - _Requirements: 11.3, 11.4, 11.5_
  
  - [ ]* 11.2 Escribir property test para exclusión de inactivos
    - **Property 32: Inactive Subscribers Excluded**
    - **Validates: Requirements 11.4**

- [ ] 12. Crear landing page estática
  - [~] 12.1 Diseñar HTML/CSS para landing page
    - Crear formulario de suscripción
    - Agregar sección de preview de newsletter
    - Incluir información sobre frecuencias disponibles
    - _Requirements: 1.5, 8.1_
  
  - [~] 12.2 Implementar JavaScript para integración con API
    - Conectar formulario con POST /subscribe
    - Cargar sample newsletter con GET /sample-newsletter
    - Mostrar mensajes de confirmación/error
    - _Requirements: 1.1, 8.1_
  
  - [~] 12.3 Configurar S3 + CloudFront para hosting
    - Subir archivos estáticos a S3
    - Configurar CloudFront distribution
    - Agregar outputs en template.yaml
    - _Requirements: 8.1_

- [ ] 13. Implementar optimizaciones de performance
  - [~] 13.1 Agregar batch processing para envío de emails
    - Implementar procesamiento en lotes de 50 suscriptores
    - Usar invocaciones concurrentes de Lambda si >1000 suscriptores
    - _Requirements: 12.5, 12.6_
  
  - [~] 13.2 Configurar GSI en DynamoDB para queries eficientes
    - Crear índice frequency-active-index
    - Optimizar queries de suscriptores activos
    - _Requirements: 5.5_

- [ ]* 14. Agregar logging y monitoreo completo
  - [~]* 14.1 Implementar logging estructurado en todas las Lambdas
    - Agregar logs con timestamp, component name, error details
    - Implementar log_newsletter_metrics()
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_
  
  - [~]* 14.2 Configurar CloudWatch alarms para fallos críticos
    - Crear alarma para 3+ fallos consecutivos de servicios
    - Configurar notificaciones SNS
    - _Requirements: 10.6_

- [ ]* 15. Implementar seguridad y validaciones finales
  - [~]* 15.1 Configurar rate limiting en API Gateway
    - Limitar a 100 requests/minuto por IP
    - Agregar throttling en endpoints públicos
    - _Requirements: 11.5_
  
  - [~]* 15.2 Implementar sanitización de HTML
    - Validar y limpiar HTML generado por IA
    - Prevenir XSS en contenido de newsletter
    - _Requirements: 4.6_
  
  - [~]* 15.3 Configurar encriptación en DynamoDB
    - Habilitar encryption at rest con KMS
    - Configurar manejo seguro de API keys en Secrets Manager
    - _Requirements: Data Protection_

- [~] 16. Final checkpoint - Testing end-to-end completo
  - Ejecutar flujo completo: suscripción → welcome email → newsletter diario → unsubscribe
  - Verificar todos los endpoints de API
  - Validar landing page funcional
  - Revisar logs y métricas en CloudWatch
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marcadas con `*` son opcionales (property tests) y pueden omitirse para MVP rápido
- Priorizar tareas 1-8 para tener funcionalidad core en el vibe racing
- Landing page (tarea 12) puede simplificarse o hacerse después del MVP
- Optimizaciones de performance (tarea 13) son importantes pero no bloqueantes
- Cada tarea referencia requirements específicos para trazabilidad
- Checkpoints aseguran validación incremental del sistema
- Para el vibe racing, enfocarse en: infraestructura, suscripción, scraping básico, generación con IA, y envío de emails
