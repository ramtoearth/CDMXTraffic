# CDMX Traffic Newsletter

Sistema automatizado de newsletter que recopila información sobre incidentes viales en Ciudad de México mediante web scraping e IA, y envía newsletters personalizadas a suscriptores.

## Arquitectura

- **AWS SAM**: Infrastructure as Code
- **Lambda**: Funciones serverless para toda la lógica
- **DynamoDB**: Almacenamiento de suscriptores
- **S3**: Archivo de newsletters
- **API Gateway**: Endpoints REST
- **EventBridge**: Triggers programados (diario a las 7 AM)
- **Secrets Manager**: Gestión segura de API keys

## Estructura del Proyecto

```
.
├── template.yaml              # SAM template principal
├── samconfig.toml            # Configuración de despliegue
├── requirements.txt          # Dependencias Python
├── src/
│   ├── subscribe/           # Lambda: Suscripción de usuarios
│   ├── scraper/             # Lambda: Web scraping de datos de tráfico
│   ├── ai_generator/        # Lambda: Generación de contenido con IA
│   ├── generate_newsletter/ # Lambda: Orquestación del newsletter
│   ├── send_email/          # Lambda: Envío de emails vía Zavu.dev
│   ├── get_sample/          # Lambda: Obtener newsletter de ejemplo
│   └── unsubscribe/         # Lambda: Cancelar suscripción
└── .kiro/specs/             # Especificaciones del proyecto
```

## Recursos de AWS

### DynamoDB Table: Subscribers
- **Partition Key**: subscriber_id (String)
- **GSI**: email-index (para búsqueda por email)
- **GSI**: frequency-active-index (para consultas de suscriptores activos)
- **Campos**: subscriber_id, email, name, frequency, subscribed_at, last_sent_at, active, unsubscribe_token

### S3 Bucket: Newsletter Archive
- **Formato de keys**: newsletters/YYYY/MM/DD/{newsletter_id}.html
- **Acceso**: Público para lectura de newsletters
- **Lifecycle**: Eliminación automática después de 365 días

### API Gateway Endpoints
- `POST /subscribe` - Suscribirse al newsletter
- `GET /sample-newsletter` - Obtener newsletter de ejemplo
- `POST /unsubscribe` - Cancelar suscripción

### EventBridge Schedule
- **Frecuencia**: Diario a las 7:00 AM (hora de Ciudad de México)
- **Cron**: `cron(0 13 * * ? *)` (13:00 UTC = 7:00 AM CDMX)

## Requisitos Previos

1. **AWS CLI** instalado y configurado
2. **AWS SAM CLI** instalado
3. **Python 3.11** o superior
4. **Cuenta de AWS** con permisos apropiados
5. **API Keys**:
   - Zavu.dev API key (para envío de emails)
   - OpenAI API key (para generación de contenido con IA)

## Instalación

### 1. Instalar AWS SAM CLI

```bash
# macOS
brew install aws-sam-cli

# Linux
pip install aws-sam-cli

# Windows
choco install aws-sam-cli
```

### 2. Configurar AWS CLI

```bash
aws configure
# Ingresa tu AWS Access Key ID
# Ingresa tu AWS Secret Access Key
# Región: us-east-1 (o tu región preferida)
```

### 3. Clonar el repositorio

```bash
git clone <repository-url>
cd cdmx-traffic-newsletter
```

## Despliegue

### Despliegue Inicial (Dev)

```bash
# Validar el template
sam validate

# Build de las funciones Lambda
sam build

# Desplegar (primera vez - modo guiado)
sam deploy --guided

# Despliegues subsecuentes
sam deploy
```

### Despliegue a Staging/Prod

```bash
# Staging
sam deploy --config-env staging

# Producción
sam deploy --config-env prod
```

## Configuración de Secrets

Después del despliegue, debes actualizar los secrets con tus API keys reales:

### Zavu.dev API Key

```bash
aws secretsmanager update-secret \
  --secret-id dev/cdmx-traffic/zavu-api-key \
  --secret-string '{"api_key":"TU_ZAVU_API_KEY_AQUI"}'
```

### OpenAI API Key

```bash
aws secretsmanager update-secret \
  --secret-id dev/cdmx-traffic/openai-api-key \
  --secret-string '{"api_key":"TU_OPENAI_API_KEY_AQUI"}'
```

## Desarrollo Local

### Invocar Lambda localmente

```bash
# Invocar función de suscripción
sam local invoke SubscribeFunction -e events/subscribe.json

# Iniciar API Gateway local
sam local start-api

# Probar endpoint
curl -X POST http://localhost:3000/subscribe \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","frequency":"daily"}'
```

### Logs

```bash
# Ver logs de una función específica
sam logs -n SubscribeFunction --stack-name cdmx-traffic-newsletter --tail

# Ver logs de todas las funciones
sam logs --stack-name cdmx-traffic-newsletter --tail
```

## Testing

```bash
# Instalar dependencias de testing
pip install -r requirements-dev.txt

# Ejecutar tests unitarios
pytest tests/unit/

# Ejecutar tests de integración
pytest tests/integration/

# Ejecutar tests con coverage
pytest --cov=src tests/
```

## Monitoreo

### CloudWatch Dashboards

Los logs de todas las funciones Lambda están disponibles en CloudWatch:
- Retention: 30 días
- Log Groups: `/aws/lambda/{function-name}`

### Métricas Clave

- Tasa de suscripciones exitosas
- Tasa de entrega de emails
- Tiempo de ejecución de scraping
- Errores de generación de IA
- Conteo de incidentes por día

## Limpieza

Para eliminar todos los recursos de AWS:

```bash
sam delete --stack-name cdmx-traffic-newsletter
```

## Próximos Pasos

1. Implementar lógica de negocio en cada Lambda function
2. Configurar fuentes de datos para web scraping
3. Integrar con Zavu.dev API
4. Integrar con OpenAI/Bedrock para generación de contenido
5. Crear landing page estática
6. Configurar CloudFront para distribución
7. Implementar tests unitarios y de integración
8. Configurar CI/CD pipeline

## Documentación Adicional

- [Especificaciones del Proyecto](.kiro/specs/cdmx-traffic-newsletter/)
- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)
- [Zavu.dev API Docs](https://docs.zavu.dev/)

## Soporte

Para preguntas o problemas, consulta la documentación en `.kiro/specs/cdmx-traffic-newsletter/`.
