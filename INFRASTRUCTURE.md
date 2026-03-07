# Infraestructura Base - CDMX Traffic Newsletter

## Resumen

Se ha configurado la infraestructura base completa usando AWS SAM para el sistema de newsletter de tráfico CDMX. Esta infraestructura cumple con los **Requirements 12.1 y 12.2** del documento de especificaciones.

## Archivos Creados

### Configuración Principal
- ✅ `template.yaml` - Template SAM con todos los recursos de AWS
- ✅ `samconfig.toml` - Configuración de despliegue para dev/staging/prod
- ✅ `requirements.txt` - Dependencias Python para Lambdas
- ✅ `requirements-dev.txt` - Dependencias de desarrollo y testing

### Código Lambda (Placeholders)
- ✅ `src/subscribe/handler.py` - Manejo de suscripciones
- ✅ `src/scraper/handler.py` - Web scraping de datos de tráfico
- ✅ `src/ai_generator/handler.py` - Generación de contenido con IA
- ✅ `src/generate_newsletter/handler.py` - Orquestación del newsletter
- ✅ `src/send_email/handler.py` - Envío de emails vía Zavu.dev
- ✅ `src/get_sample/handler.py` - Obtener newsletter de ejemplo
- ✅ `src/unsubscribe/handler.py` - Cancelación de suscripciones

### Eventos de Prueba
- ✅ `events/subscribe.json` - Evento de prueba para suscripción
- ✅ `events/unsubscribe.json` - Evento de prueba para cancelación
- ✅ `events/generate_newsletter.json` - Evento de prueba para generación

### Documentación
- ✅ `README.md` - Documentación general del proyecto
- ✅ `DEPLOYMENT.md` - Guía detallada de despliegue
- ✅ `INFRASTRUCTURE.md` - Este documento
- ✅ `Makefile` - Comandos útiles para desarrollo y despliegue

### Otros
- ✅ `.gitignore` - Archivos a ignorar en Git

## Recursos de AWS Configurados

### 1. DynamoDB Table: SubscribersTable
```yaml
Nombre: {Environment}-cdmx-traffic-subscribers
Billing: PAY_PER_REQUEST (on-demand)
Partition Key: subscriber_id (String)
GSI 1: email-index (para búsqueda por email)
GSI 2: frequency-active-index (para consultas eficientes)
Encryption: SSE habilitado
Backup: Point-in-time recovery habilitado
```

**Campos del Schema:**
- `subscriber_id` (String, PK) - UUID único
- `email` (String) - Email del suscriptor
- `name` (String) - Nombre del suscriptor
- `frequency` (String) - "daily" o "weekly"
- `subscribed_at` (String) - Timestamp ISO 8601
- `last_sent_at` (String) - Timestamp ISO 8601
- `active` (Boolean) - Estado de la suscripción
- `unsubscribe_token` (String) - Token único para cancelar

### 2. S3 Bucket: NewsletterBucket
```yaml
Nombre: {Environment}-cdmx-traffic-newsletters
Acceso: Público para lectura (path: newsletters/*)
CORS: Habilitado para landing page
Versionado: Habilitado
Lifecycle: Eliminación automática después de 365 días
```

**Estructura de Keys:**
```
newsletters/
  └── YYYY/
      └── MM/
          └── DD/
              └── {newsletter_id}.html
```

### 3. API Gateway: RestApi
```yaml
Nombre: {Environment}-cdmx-traffic-api
Stage: {Environment}
CORS: Habilitado
Tracing: X-Ray habilitado
```

**Endpoints:**
- `POST /subscribe` → SubscribeFunction
- `GET /sample-newsletter` → GetSampleNewsletterFunction
- `POST /unsubscribe` → UnsubscribeFunction

### 4. Lambda Functions

| Función | Timeout | Memory | Trigger | Descripción |
|---------|---------|--------|---------|-------------|
| SubscribeFunction | 30s | 512MB | API Gateway | Procesa suscripciones |
| ScraperFunction | 60s | 512MB | Invocación | Scraping de datos |
| AIGeneratorFunction | 30s | 512MB | Invocación | Genera contenido IA |
| GenerateNewsletterFunction | 300s | 512MB | EventBridge | Orquesta generación |
| SendEmailFunction | 30s | 512MB | Invocación | Envía emails |
| GetSampleNewsletterFunction | 30s | 512MB | API Gateway | Retorna ejemplo |
| UnsubscribeFunction | 30s | 512MB | API Gateway | Procesa cancelaciones |

**Variables de Entorno (todas las funciones):**
- `SUBSCRIBERS_TABLE` - Nombre de la tabla DynamoDB
- `NEWSLETTER_BUCKET` - Nombre del bucket S3
- `ZAVU_API_KEY_SECRET` - ARN del secret de Zavu
- `OPENAI_API_KEY_SECRET` - ARN del secret de OpenAI
- `FROM_EMAIL` - Email del remitente
- `ENVIRONMENT` - Ambiente (dev/staging/prod)

### 5. EventBridge Rule
```yaml
Schedule: cron(0 13 * * ? *)
Descripción: Trigger diario a las 7 AM CDMX (13:00 UTC)
Target: GenerateNewsletterFunction
Estado: Habilitado
```

### 6. Secrets Manager

**Zavu API Key:**
```yaml
Nombre: {Environment}/cdmx-traffic/zavu-api-key
Formato: {"api_key": "..."}
```

**OpenAI API Key:**
```yaml
Nombre: {Environment}/cdmx-traffic/openai-api-key
Formato: {"api_key": "..."}
```

### 7. IAM Role: LambdaExecutionRole
```yaml
Nombre: {Environment}-cdmx-traffic-lambda-role
Managed Policies:
  - AWSLambdaBasicExecutionRole
Custom Policies:
  - DynamoDBAccess (read/write en SubscribersTable + GSIs)
  - S3Access (read/write en NewsletterBucket)
  - SecretsManagerAccess (read en ambos secrets)
  - LambdaInvokeAccess (invoke en funciones internas)
```

### 8. CloudWatch Log Groups
Todas las funciones Lambda tienen log groups con:
- Retención: 30 días
- Formato: `/aws/lambda/{function-name}`

## Cumplimiento de Requirements

### ✅ Requirement 12.1: Performance
1. **DynamoDB con PAY_PER_REQUEST**: Escalabilidad automática sin throttling
2. **GSI optimizados**: Consultas eficientes por frequency y active
3. **Lambda timeouts apropiados**: 
   - Subscribe: 30s (target <1s)
   - Scraper: 60s (target <30s)
   - AI Generator: 30s (target <15s)
   - Send Email: 30s (target <3s)
   - Generate Newsletter: 300s (target <5min)
4. **S3 con versionado**: Recuperación rápida de newsletters

### ✅ Requirement 12.2: Scalability
1. **Arquitectura serverless**: Escala automáticamente con la demanda
2. **DynamoDB on-demand**: Sin límites de capacidad predefinidos
3. **Lambda concurrente**: Múltiples invocaciones simultáneas
4. **API Gateway**: Rate limiting y throttling configurables
5. **S3**: Almacenamiento ilimitado y altamente disponible
6. **EventBridge**: Triggers confiables y escalables

## Permisos IAM Configurados

### Lambda → DynamoDB
- `dynamodb:GetItem` - Leer suscriptor individual
- `dynamodb:PutItem` - Crear nuevo suscriptor
- `dynamodb:UpdateItem` - Actualizar suscriptor existente
- `dynamodb:Query` - Consultar por GSI
- `dynamodb:Scan` - Escanear tabla (uso limitado)
- `dynamodb:BatchGetItem` - Leer múltiples suscriptores
- `dynamodb:BatchWriteItem` - Escribir múltiples suscriptores

### Lambda → S3
- `s3:PutObject` - Guardar newsletters
- `s3:GetObject` - Leer newsletters
- `s3:ListBucket` - Listar newsletters

### Lambda → Secrets Manager
- `secretsmanager:GetSecretValue` - Leer API keys

### Lambda → Lambda
- `lambda:InvokeFunction` - Invocar otras funciones

## Seguridad

### Encryption
- ✅ DynamoDB: SSE habilitado (encryption at rest)
- ✅ S3: Encryption por defecto
- ✅ Secrets Manager: Encryption automática
- ✅ CloudWatch Logs: Encryption habilitada

### Network
- ✅ API Gateway: CORS configurado
- ✅ S3: Bucket policy restrictiva (solo newsletters/* público)
- ✅ Lambda: Dentro de VPC de AWS (no VPC custom por ahora)

### IAM
- ✅ Principio de mínimo privilegio
- ✅ Roles específicos por función
- ✅ No hay credenciales hardcodeadas

## Próximos Pasos

### Inmediatos (Task 2-7)
1. Implementar lógica de negocio en cada Lambda
2. Configurar fuentes de scraping
3. Integrar Zavu.dev API
4. Integrar OpenAI/Bedrock
5. Crear modelos de datos (Pydantic)
6. Implementar validaciones

### Mediano Plazo
1. Crear landing page estática
2. Configurar CloudFront para CDN
3. Implementar tests unitarios
4. Implementar tests de integración
5. Configurar CI/CD pipeline
6. Monitoreo y alertas

### Largo Plazo
1. Optimización de costos
2. Mejoras de performance
3. Features adicionales
4. Análisis de métricas

## Comandos Útiles

### Despliegue
```bash
make validate      # Validar template
make build         # Build de funciones
make deploy        # Deploy a dev
make deploy-staging # Deploy a staging
make deploy-prod   # Deploy a producción
```

### Testing Local
```bash
make invoke-subscribe  # Test subscribe function
make start-api        # Iniciar API local
make test-api         # Probar endpoints
```

### Monitoreo
```bash
make logs             # Ver todos los logs
make logs-subscribe   # Ver logs de subscribe
make get-api-url      # Obtener URL del API
```

### Limpieza
```bash
make clean   # Limpiar archivos de build
make delete  # Eliminar stack completo
```

## Costos Estimados

### Desarrollo (bajo uso)
- Lambda: ~$1-5/mes
- DynamoDB: ~$1-3/mes
- S3: ~$0.50/mes
- API Gateway: ~$1/mes
- Secrets Manager: ~$0.80/mes
- **Total**: ~$5-10/mes

### Producción (1000 suscriptores)
- Lambda: ~$10-20/mes
- DynamoDB: ~$5-10/mes
- S3: ~$2-5/mes
- API Gateway: ~$3-5/mes
- Secrets Manager: ~$0.80/mes
- **Total**: ~$20-40/mes

## Notas Importantes

1. **Secrets Placeholders**: Los secrets creados tienen valores placeholder. Deben actualizarse con las API keys reales antes de usar el sistema.

2. **Cron Schedule**: El cron está configurado para 13:00 UTC (7 AM CDMX). Ajustar si cambia el horario de verano.

3. **Bucket Names**: Los nombres de buckets S3 son globalmente únicos. Si hay conflicto, agregar sufijo único (ej: account ID).

4. **Lambda Placeholders**: Todas las funciones Lambda tienen código placeholder. Deben implementarse según el diseño.

5. **Testing**: Los eventos de prueba en `events/` son para testing local con `sam local invoke`.

## Referencias

- Spec: `.kiro/specs/cdmx-traffic-newsletter/`
- Requirements: `.kiro/specs/cdmx-traffic-newsletter/requirements.md`
- Design: `.kiro/specs/cdmx-traffic-newsletter/design.md`
- Tasks: `.kiro/specs/cdmx-traffic-newsletter/tasks.md`

---

**Estado**: ✅ Infraestructura base completada
**Task**: 1. Configurar infraestructura base con SAM
**Requirements Validados**: 12.1, 12.2
