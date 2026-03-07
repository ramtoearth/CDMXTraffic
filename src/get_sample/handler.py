"""
Get Sample Newsletter Lambda Handler
Returns latest newsletter for landing page preview
"""
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Returns latest newsletter from S3 archive
    
    Returns HTML content with CORS headers
    """
    logger.info("Fetching sample newsletter")
    
    # Placeholder implementation
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>CDMX Traffic Newsletter - Sample</title>
        <meta charset="utf-8">
    </head>
    <body>
        <h1>🚦 Newsletter de Tráfico CDMX</h1>
        <p>Este es un ejemplo de newsletter. El contenido real será generado por IA.</p>
        <p><em>Placeholder - to be implemented</em></p>
    </body>
    </html>
    """
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/html',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': sample_html
    }
