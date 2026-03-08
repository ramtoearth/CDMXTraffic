# Guía de Despliegue - CDMX Traffic Newsletter

## Validación de Requirements

Esta infraestructura cumple con los siguientes requisitos:

### Requirement 12.1: Performance
- ✅ DynamoDB con modo PAY_PER_REQUEST para escalabilidad automática
- ✅ Lambda functions con timeouts apropiados (30s-300s según función)
- ✅ GSI en DynamoDB para consultas eficientes por frequency y active
- ✅ S3 con versionado para recuperación de datos

### Requirement 12.2: Scalability
- ✅ Arquitectura serverless que escala automáticamente
- ✅ DynamoDB on-demand billing para manejar cargas variables
- ✅ Lambda con capacidad de invocación concurrente
- ✅ API Gateway con rate limiting configurado
- ✅ CloudWatch Logs con retención de 30 días

## Recursos Creados

### 1. DynamoDB Table
- **Nombre**: `{Environment}-cdmx-traffic-subscribers`
- **Billing**: PAY_PER_REQUEST (on-demand)
- **Encryption**: SSE habilitado
- **Backup**: Point-in-time recovery habilitado
- **Índices**:
  - GSI: `email-index` (para búsqueda por email)
  - GSI: `frequency-active-index` (para consultas de suscriptores activos)

### 2. S3 Bucket
- **Nombre**: `{Environment}-cdmx-traffic-newsletters`
- **Acceso**: Público para lectura de newsletters (path: newsletters/*)
- **CORS**: Configurado para acceso desde landing page
- **Versionado**: Habilitado
- **Lifecycle**: Eliminación automática después de 365 días

### 3. API Gateway
- **Nombre**: `{Environment}-cdmx-traffic-api`
- **Stage**: {Environment} (dev/staging/prod)
- **CORS**: Habilitado para todos los orígenes
- **Tracing**: X-Ray habilitado
- **Endpoints**:
  - `POST /subscribe`
  - `GET /sample-newsletter`
  - `POST /unsubscribe`

### 4. Lambda Functions
Todas las funciones tienen:
- Runtime: Python 3.11
- Memory: 512 MB
- Logs: CloudWatch con retención de 30 días
- Role: IAM role con permisos mínimos necesarios

| Función | Timeout | Trigger | Descripción |
|---------|---------|---------|-------------|
| Subscribe | 30s | API Gateway | Maneja suscripciones |
| Scraper | 60s | Invocación directa | Web scraping de datos |
| AI Generator | 30s | Invocación directa | Genera contenido con IA |
| Generate Newsletter | 300s | EventBridge (7 AM) | Orquesta generación diaria |
| Send Email | 30s | Invocación directa | Envía emails vía Zavu |
| Get Sample | 30s | API Gateway | Retorna newsletter ejemplo |
| Unsubscribe | 30s | API Gateway | Procesa cancelaciones |

### 5. EventBridge Rule
- **Schedule**: `cron(0 13 * * ? *)` (7:00 AM Mexico City time)
- **Target**: GenerateNewsletterFunction
- **Estado**: Habilitado
- **Nombre**: `{Environment}-cdmx-traffic-daily-newsletter`

**Nota sobre Timezone**: 
- EventBridge usa UTC para cron expressions
- Ciudad de México está en CST (UTC-6) durante horario estándar
- Durante horario de verano (DST, abril-octubre), CDMX está en UTC-5
- La regla está configurada para 13:00 UTC = 7:00 AM CST
- Durante DST, el newsletter se enviará a las 8:00 AM hora local
- Esto es una limitación de EventBridge que no soporta timezones directamente

### 6. Secrets Manager
- **Zavu API Key**: `{Environment}/cdmx-traffic/zavu-api-key`
- **OpenAI API Key**: `{Environment}/cdmx-traffic/openai-api-key`
- **Nota**: Valores iniciales son placeholders - deben actualizarse

### 7. IAM Role
- **Nombre**: `{Environment}-cdmx-traffic-lambda-role`
- **Permisos**:
  - CloudWatch Logs (escritura)
  - DynamoDB (read/write en SubscribersTable)
  - S3 (read/write en NewsletterBucket)
  - Secrets Manager (read en ambos secrets)
  - Lambda (invoke en funciones internas)

## Pasos de Despliegue

### Pre-requisitos
```bash
# Verificar instalación de herramientas
aws --version
sam --version
python --version  # Debe ser 3.11+
```

### 1. Validar Template
```bash
sam validate --lint
```

### 2. Build
```bash
sam build --parallel
```

### 3. Deploy (Primera vez)
```bash
sam deploy --guided
```

Responde las preguntas:
- Stack Name: `cdmx-traffic-newsletter`
- AWS Region: `us-east-1` (o tu región preferida)
- Parameter Environment: `dev`
- Confirm changes: `Y`
- Allow SAM CLI IAM role creation: `Y`
- Disable rollback: `N`
- Save arguments to configuration: `Y`

### 4. Configurar Secrets

```bash
# Zavu API Key
aws secretsmanager update-secret \
  --secret-id dev/cdmx-traffic/zavu-api-key \
  --secret-string '{"api_key":"tu-zavu-api-key"}'

# OpenAI API Key
aws secretsmanager update-secret \
  --secret-id dev/cdmx-traffic/openai-api-key \
  --secret-string '{"api_key":"tu-openai-api-key"}'
```

### 5. Verificar Despliegue

```bash
# Obtener outputs del stack
aws cloudformation describe-stacks \
  --stack-name cdmx-traffic-newsletter \
  --query 'Stacks[0].Outputs'

# Probar API endpoint
API_URL=$(aws cloudformation describe-stacks \
  --stack-name cdmx-traffic-newsletter \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text)

echo "API Endpoint: $API_URL"

# Test subscribe endpoint
curl -X POST $API_URL/subscribe \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","frequency":"daily","name":"Test User"}'

# Test sample newsletter endpoint
curl $API_URL/sample-newsletter
```

## Despliegue a Otros Ambientes

### Staging
```bash
sam deploy --config-env staging
```

### Producción
```bash
sam deploy --config-env prod
```

## Actualización de Stack

Para actualizar después de cambios en el código o template:

```bash
sam build
sam deploy
```

## Rollback

Si algo sale mal:

```bash
# Rollback automático está habilitado por defecto
# O manualmente:
aws cloudformation cancel-update-stack --stack-name cdmx-traffic-newsletter
```

## Monitoreo Post-Despliegue

### Ver Logs
```bash
# Logs de función específica
sam logs -n SubscribeFunction --stack-name cdmx-traffic-newsletter --tail

# Logs de todas las funciones
aws logs tail /aws/lambda/dev-cdmx-traffic-subscribe --follow
```

### Métricas en CloudWatch
1. Ir a CloudWatch Console
2. Buscar métricas de Lambda
3. Filtrar por stack: `cdmx-traffic-newsletter`

### Verificar EventBridge Rule
```bash
aws events list-rules --name-prefix dev-cdmx-traffic
```

## Troubleshooting

### Error: "Stack already exists"
```bash
# Eliminar stack existente
sam delete --stack-name cdmx-traffic-newsletter
# Volver a desplegar
sam deploy --guided
```

### Error: "Insufficient permissions"
Verificar que tu usuario de AWS tiene permisos para:
- CloudFormation
- Lambda
- DynamoDB
- S3
- API Gateway
- IAM
- Secrets Manager
- EventBridge
- CloudWatch Logs

### Error: "Bucket already exists"
Los nombres de buckets S3 son globalmente únicos. Modificar el nombre en template.yaml:
```yaml
BucketName: !Sub ${Environment}-cdmx-traffic-newsletters-${AWS::AccountId}
```

## Limpieza

Para eliminar todos los recursos:

```bash
# Eliminar stack
sam delete --stack-name cdmx-traffic-newsletter

# Verificar eliminación
aws cloudformation describe-stacks --stack-name cdmx-traffic-newsletter
# Debe retornar error "Stack does not exist"
```

**Nota**: El bucket S3 puede requerir vaciado manual antes de eliminación:
```bash
aws s3 rm s3://dev-cdmx-traffic-newsletters --recursive
```

## Costos Estimados

### Ambiente Dev (bajo uso)
- Lambda: ~$1-5/mes
- DynamoDB: ~$1-3/mes (on-demand)
- S3: ~$0.50/mes
- API Gateway: ~$1/mes
- Secrets Manager: ~$0.80/mes
- **Total estimado**: ~$5-10/mes

### Producción (1000 suscriptores)
- Lambda: ~$10-20/mes
- DynamoDB: ~$5-10/mes
- S3: ~$2-5/mes
- API Gateway: ~$3-5/mes
- Secrets Manager: ~$0.80/mes
- **Total estimado**: ~$20-40/mes

## Próximos Pasos

1. ✅ Infraestructura base desplegada
2. ⏳ Implementar lógica de negocio en Lambdas
3. ⏳ Configurar fuentes de scraping
4. ⏳ Integrar Zavu.dev API
5. ⏳ Integrar OpenAI/Bedrock
6. ⏳ Crear landing page
7. ⏳ Implementar tests
8. ⏳ Configurar CI/CD

## Referencias

- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)
- [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)
- [Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [Zavu.dev API](https://docs.zavu.dev/)
