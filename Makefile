.PHONY: help validate build deploy deploy-guided deploy-frontend test clean logs invoke-local start-api

help: ## Mostrar esta ayuda
	@echo "Comandos disponibles:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

validate: ## Validar el template SAM
	sam validate --lint

build: ## Build de las funciones Lambda
	sam build --parallel

deploy: build ## Deploy del stack (usa samconfig.toml)
	sam deploy

deploy-guided: build ## Deploy guiado (primera vez)
	sam deploy --guided

deploy-staging: build ## Deploy a staging
	sam deploy --config-env staging

deploy-prod: build ## Deploy a producción
	sam deploy --config-env prod

test: ## Ejecutar tests
	pytest tests/ -v

test-coverage: ## Ejecutar tests con coverage
	pytest tests/ --cov=src --cov-report=html --cov-report=term

clean: ## Limpiar archivos de build
	rm -rf .aws-sam/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

logs: ## Ver logs de todas las funciones
	sam logs --stack-name cdmx-traffic-newsletter --tail

logs-subscribe: ## Ver logs de Subscribe function
	sam logs -n SubscribeFunction --stack-name cdmx-traffic-newsletter --tail

logs-generate: ## Ver logs de Generate Newsletter function
	sam logs -n GenerateNewsletterFunction --stack-name cdmx-traffic-newsletter --tail

invoke-subscribe: ## Invocar Subscribe function localmente
	sam local invoke SubscribeFunction -e events/subscribe.json

invoke-generate: ## Invocar Generate Newsletter function localmente
	sam local invoke GenerateNewsletterFunction -e events/generate_newsletter.json

start-api: ## Iniciar API Gateway local
	sam local start-api

delete: ## Eliminar el stack
	sam delete --stack-name cdmx-traffic-newsletter

update-secrets: ## Actualizar secrets (requiere variables de entorno)
	@echo "Actualizando Zavu API Key..."
	@aws secretsmanager update-secret \
		--secret-id dev/cdmx-traffic/zavu-api-key \
		--secret-string "{\"api_key\":\"$$ZAVU_API_KEY\"}"
	@echo "Actualizando OpenAI API Key..."
	@aws secretsmanager update-secret \
		--secret-id dev/cdmx-traffic/openai-api-key \
		--secret-string "{\"api_key\":\"$$OPENAI_API_KEY\"}"
	@echo "Secrets actualizados exitosamente"

deploy-frontend: ## Deploy landing page to S3 and invalidate CloudFront
	@API_URL=$$(aws cloudformation describe-stacks \
		--stack-name cdmx-traffic-newsletter \
		--query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
		--output text); \
	BUCKET=$$(aws cloudformation describe-stacks \
		--stack-name cdmx-traffic-newsletter \
		--query 'Stacks[0].Outputs[?OutputKey==`LandingPageBucketName`].OutputValue' \
		--output text); \
	CF_ID=$$(aws cloudformation describe-stacks \
		--stack-name cdmx-traffic-newsletter \
		--query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDistributionId`].OutputValue' \
		--output text); \
	echo "API URL: $$API_URL"; \
	echo "Bucket:  $$BUCKET"; \
	echo "CF ID:   $$CF_ID"; \
	sed "s|PLACEHOLDER_API_URL|$$API_URL|g" frontend/config.js > /tmp/cdmx-config.js; \
	aws s3 cp frontend/index.html s3://$$BUCKET/index.html --content-type text/html; \
	aws s3 cp /tmp/cdmx-config.js s3://$$BUCKET/config.js --content-type application/javascript; \
	aws cloudfront create-invalidation --distribution-id $$CF_ID --paths "/*"; \
	echo "Frontend deployed. URL: $$(aws cloudformation describe-stacks \
		--stack-name cdmx-traffic-newsletter \
		--query 'Stacks[0].Outputs[?OutputKey==`LandingPageUrl`].OutputValue' \
		--output text)"

get-api-url: ## Obtener URL del API Gateway
	@aws cloudformation describe-stacks \
		--stack-name cdmx-traffic-newsletter \
		--query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
		--output text

test-api: ## Probar API endpoints
	@API_URL=$$(make get-api-url); \
	echo "Testing POST /subscribe..."; \
	curl -X POST $$API_URL/subscribe \
		-H "Content-Type: application/json" \
		-d '{"email":"test@example.com","frequency":"daily","name":"Test User"}'; \
	echo "\n\nTesting GET /sample-newsletter..."; \
	curl $$API_URL/sample-newsletter

install-deps: ## Instalar dependencias de desarrollo
	pip install -r requirements.txt
	pip install pytest pytest-cov moto boto3-stubs

format: ## Formatear código con black
	black src/ tests/

lint: ## Lint del código
	flake8 src/ tests/
	pylint src/

setup-dev: install-deps ## Setup completo para desarrollo
	@echo "Ambiente de desarrollo configurado"
