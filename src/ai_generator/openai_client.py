"""
OpenAI API client for newsletter content generation

Requirements validated:
- 4.1: Generate content from traffic incidents using LLM
- 4.2: Generate relevant subject line
- 4.3: Create executive summary
- 4.5: Handle empty incidents list
"""
import os
import json
import logging

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

NEWSLETTER_PROMPT_TEMPLATE = """\
Eres un asistente de noticias de tráfico para Ciudad de México. \
Genera un newsletter profesional y amigable en español basado en los incidentes viales del día.

Incidentes de hoy:
{incidents_text}

Responde ÚNICAMENTE con un objeto JSON con la siguiente estructura (sin texto adicional, sin markdown):
{{
    "subject": "Asunto del email (máximo 80 caracteres)",
    "summary": "Resumen ejecutivo de 2-3 oraciones sobre la situación del tráfico",
    "highlights": ["Punto clave 1", "Punto clave 2", "Punto clave 3"],
    "html_body": "HTML completo del newsletter con estilos inline",
    "text_body": "Versión en texto plano del newsletter"
}}

Reglas:
- El subject debe ser conciso, descriptivo e incluir la fecha si es relevante
- El summary debe dar una visión general clara de la situación vial
- Los highlights deben contener entre 3 y 5 puntos, priorizando los incidentes más graves
- El html_body debe tener estilos inline apropiados para email (no usar <script> ni event handlers)
- El text_body no debe contener etiquetas HTML
- Responde en español mexicano
"""

NO_INCIDENTS_PROMPT = """\
Eres un asistente de noticias de tráfico para Ciudad de México.
Hoy no se registraron incidentes viales significativos.

Genera un newsletter breve indicando que el tráfico fluye con normalidad.

Responde ÚNICAMENTE con un objeto JSON (sin texto adicional, sin markdown):
{
    "subject": "CDMX Tráfico - Sin incidentes significativos hoy",
    "summary": "No se registraron incidentes viales significativos en Ciudad de México. El tráfico fluye con normalidad en la mayor parte de la ciudad.",
    "highlights": ["Tráfico fluye con normalidad en toda la ciudad"],
    "html_body": "HTML completo del newsletter indicando sin incidentes",
    "text_body": "Texto plano indicando que no hay incidentes"
}
"""


def get_openai_api_key() -> str:
    """
    Retrieve OpenAI API key from AWS Secrets Manager.

    Returns:
        API key string

    Raises:
        Exception: If unable to retrieve secret
    """
    secret_name = os.environ.get(
        "OPENAI_API_KEY_SECRET", "dev/cdmx-traffic/openai-api-key"
    )
    region = os.environ.get("AWS_REGION", "us-east-1")

    try:
        client = boto3.session.Session().client(
            service_name="secretsmanager", region_name=region
        )
        response = client.get_secret_value(SecretId=secret_name)

        if "SecretString" in response:
            secret = response["SecretString"]
            try:
                secret_dict = json.loads(secret)
                return secret_dict.get("api_key", secret)
            except (json.JSONDecodeError, AttributeError):
                return secret
        else:
            raise Exception("Secret is binary, expected string")

    except ClientError as e:
        logger.error(f"Failed to retrieve OpenAI API key from Secrets Manager: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving OpenAI API key: {e}")
        raise


def call_openai_api(prompt: str, model: str = "gpt-4o-mini") -> str:
    """
    Call OpenAI Chat Completions API with the given prompt.

    Args:
        prompt: The prompt to send to the model
        model: OpenAI model to use

    Returns:
        Raw JSON text response from the model

    Raises:
        Exception: If the API call fails
    """
    try:
        import openai  # noqa: PLC0415
    except ImportError:
        raise ImportError(
            "openai package is required. Add 'openai==1.6.0' to requirements.txt."
        )

    api_key = get_openai_api_key()
    client = openai.OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=2000,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    logger.info(
        f"OpenAI API call succeeded. Tokens used: {response.usage.total_tokens}"
    )
    return content
