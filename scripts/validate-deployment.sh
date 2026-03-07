#!/bin/bash

# Script para validar el despliegue de la infraestructura
# Usage: ./scripts/validate-deployment.sh [stack-name] [environment]

set -e

STACK_NAME=${1:-cdmx-traffic-newsletter}
ENVIRONMENT=${2:-dev}

echo "🔍 Validando despliegue de $STACK_NAME en ambiente $ENVIRONMENT..."
echo ""

# Verificar que el stack existe
echo "1. Verificando stack de CloudFormation..."
if aws cloudformation describe-stacks --stack-name $STACK_NAME &> /dev/null; then
    echo "   ✅ Stack encontrado"
    STACK_STATUS=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].StackStatus' --output text)
    echo "   Status: $STACK_STATUS"
else
    echo "   ❌ Stack no encontrado"
    exit 1
fi

echo ""

# Verificar DynamoDB table
echo "2. Verificando tabla DynamoDB..."
TABLE_NAME="${ENVIRONMENT}-cdmx-traffic-subscribers"
if aws dynamodb describe-table --table-name $TABLE_NAME &> /dev/null; then
    echo "   ✅ Tabla $TABLE_NAME existe"
    TABLE_STATUS=$(aws dynamodb describe-table --table-name $TABLE_NAME --query 'Table.TableStatus' --output text)
    echo "   Status: $TABLE_STATUS"
else
    echo "   ❌ Tabla no encontrada"
fi

echo ""

# Verificar S3 bucket
echo "3. Verificando bucket S3..."
BUCKET_NAME="${ENVIRONMENT}-cdmx-traffic-newsletters"
if aws s3 ls s3://$BUCKET_NAME &> /dev/null; then
    echo "   ✅ Bucket $BUCKET_NAME existe"
else
    echo "   ❌ Bucket no encontrado"
fi

echo ""

# Verificar Lambda functions
echo "4. Verificando funciones Lambda..."
FUNCTIONS=(
    "${ENVIRONMENT}-cdmx-traffic-subscribe"
    "${ENVIRONMENT}-cdmx-traffic-scraper"
    "${ENVIRONMENT}-cdmx-traffic-ai-generator"
    "${ENVIRONMENT}-cdmx-traffic-generate-newsletter"
    "${ENVIRONMENT}-cdmx-traffic-send-email"
    "${ENVIRONMENT}-cdmx-traffic-get-sample"
    "${ENVIRONMENT}-cdmx-traffic-unsubscribe"
)

for FUNCTION in "${FUNCTIONS[@]}"; do
    if aws lambda get-function --function-name $FUNCTION &> /dev/null; then
        echo "   ✅ $FUNCTION"
    else
        echo "   ❌ $FUNCTION no encontrada"
    fi
done

echo ""

# Verificar API Gateway
echo "5. Verificando API Gateway..."
API_ID=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
    --output text | cut -d'/' -f3 | cut -d'.' -f1)

if [ ! -z "$API_ID" ]; then
    echo "   ✅ API Gateway encontrado"
    API_URL=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
        --output text)
    echo "   URL: $API_URL"
else
    echo "   ❌ API Gateway no encontrado"
fi

echo ""

# Verificar Secrets Manager
echo "6. Verificando secrets..."
SECRETS=(
    "${ENVIRONMENT}/cdmx-traffic/zavu-api-key"
    "${ENVIRONMENT}/cdmx-traffic/openai-api-key"
)

for SECRET in "${SECRETS[@]}"; do
    if aws secretsmanager describe-secret --secret-id $SECRET &> /dev/null; then
        echo "   ✅ $SECRET"
        # Verificar si es placeholder
        SECRET_VALUE=$(aws secretsmanager get-secret-value --secret-id $SECRET --query 'SecretString' --output text)
        if echo $SECRET_VALUE | grep -q "PLACEHOLDER"; then
            echo "      ⚠️  Contiene valor PLACEHOLDER - debe actualizarse"
        fi
    else
        echo "   ❌ $SECRET no encontrado"
    fi
done

echo ""

# Verificar EventBridge rule
echo "7. Verificando EventBridge rule..."
RULE_PREFIX="${STACK_NAME}-GenerateNewsletterFunction"
RULES=$(aws events list-rules --name-prefix $RULE_PREFIX --query 'Rules[0].Name' --output text)
if [ ! -z "$RULES" ] && [ "$RULES" != "None" ]; then
    echo "   ✅ Rule encontrado: $RULES"
    RULE_STATE=$(aws events list-rules --name-prefix $RULE_PREFIX --query 'Rules[0].State' --output text)
    echo "   Estado: $RULE_STATE"
else
    echo "   ❌ Rule no encontrado"
fi

echo ""

# Verificar IAM role
echo "8. Verificando IAM role..."
ROLE_NAME="${ENVIRONMENT}-cdmx-traffic-lambda-role"
if aws iam get-role --role-name $ROLE_NAME &> /dev/null; then
    echo "   ✅ Role $ROLE_NAME existe"
else
    echo "   ❌ Role no encontrado"
fi

echo ""

# Test de conectividad API
echo "9. Probando conectividad API..."
if [ ! -z "$API_URL" ]; then
    echo "   Probando GET /sample-newsletter..."
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $API_URL/sample-newsletter)
    if [ "$HTTP_CODE" == "200" ]; then
        echo "   ✅ API responde correctamente (HTTP $HTTP_CODE)"
    else
        echo "   ⚠️  API responde con HTTP $HTTP_CODE"
    fi
else
    echo "   ⚠️  No se puede probar - API URL no disponible"
fi

echo ""
echo "=========================================="
echo "✅ Validación completada"
echo "=========================================="
echo ""
echo "Próximos pasos:"
echo "1. Actualizar secrets con API keys reales:"
echo "   make update-secrets"
echo ""
echo "2. Implementar lógica de negocio en las funciones Lambda"
echo ""
echo "3. Probar endpoints:"
echo "   make test-api"
