"""
Welcome email templates for new CDMX Traffic Newsletter subscribers.

Requirements:
    - 2.1: Send welcome newsletter to new subscribers
    - 2.2: Send welcome newsletter on reactivation
    - 11.2: Include unsubscribe link with token in every newsletter email
"""


def get_welcome_subject() -> str:
    """
    Get subject line for welcome newsletter
    
    Requirements:
        - 2.1, 2.2: Welcome newsletter subject
    """
    return "🚦 ¡Bienvenido al Boletín de Tráfico CDMX!"


def generate_welcome_html(
    name: str,
    email: str,
    frequency: str,
    unsubscribe_token: str,
    landing_url: str,
) -> str:
    """
    Generate HTML content for welcome newsletter
    
    Requirements:
        - 2.1, 2.2: Welcome newsletter content for new/reactivated subscribers
        - 11.2: Include unsubscribe link with token
    """
    freq_text = "diariamente" if frequency == "daily" else "semanalmente"
    greeting = f"Hola {name}," if name else "Hola,"

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Bienvenido al Boletin de Trafico CDMX</title>
</head>
<body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f5f5f5;">
  <table role="presentation" style="width: 100%; border-collapse: collapse;">
    <tr>
      <td align="center" style="padding: 40px 20px;">
        <table role="presentation" style="max-width: 600px; width: 100%; background-color: #ffffff; border-radius: 8px;">
          <tr>
            <td style="background-color: #e63946; padding: 40px 30px; text-align: center; border-radius: 8px 8px 0 0;">
              <h1 style="margin: 0; color: #ffffff; font-size: 28px;">
                Boletin de Trafico CDMX
              </h1>
            </td>
          </tr>
          
          <tr>
            <td style="padding: 40px 30px;">
              <p style="margin: 0 0 20px; font-size: 18px; color: #1a1a1a;">
                {greeting}
              </p>
              
              <p style="margin: 0 0 20px; font-size: 16px; color: #333333;">
                Te has suscrito exitosamente al <strong>Boletin de Trafico CDMX</strong>!
              </p>
              
              <div style="background-color: #f8f9fa; border-left: 4px solid #e63946; padding: 20px; margin: 25px 0;">
                <p style="margin: 0; font-size: 15px; color: #495057;">
                  Recibiras actualizaciones de trafico <strong>{freq_text}</strong>
                </p>
              </div>
              
              <h2 style="margin: 30px 0 20px; font-size: 20px; color: #1a1a1a;">
                Que puedes esperar?
              </h2>
              
              <ul style="margin: 20px 0; padding-left: 20px;">
                <li style="margin: 10px 0; color: #333333;">Reportes de incidentes de trafico en tiempo real</li>
                <li style="margin: 10px 0; color: #333333;">Alertas de accidentes y cierres de vialidades</li>
                <li style="margin: 10px 0; color: #333333;">Informacion sobre obras y manifestaciones</li>
                <li style="margin: 10px 0; color: #333333;">Recomendaciones para optimizar tu ruta</li>
              </ul>
            </td>
          </tr>
          
          <tr>
            <td style="background-color: #f8f9fa; padding: 30px; text-align: center; border-radius: 0 0 8px 8px;">
              <p style="margin: 0 0 10px; font-size: 13px; color: #6c757d;">
                Boletin de Trafico CDMX - Mantente informado sobre el trafico en la ciudad
              </p>
              <p style="margin: 10px 0 0; font-size: 12px; color: #868e96;">
                Para cancelar tu suscripcion, responde a este email con "CANCELAR" y tu token: {unsubscribe_token}
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def generate_welcome_text(
    name: str,
    email: str,
    frequency: str,
    unsubscribe_token: str,
    landing_url: str,
) -> str:
    """
    Generate plain text content for welcome newsletter
    
    Requirements:
        - 2.1, 2.2: Welcome newsletter content for new/reactivated subscribers
        - 11.2: Include unsubscribe link with token
    """
    freq_text = "diariamente" if frequency == "daily" else "semanalmente"
    greeting = f"Hola {name}," if name else "Hola,"

    return f"""BOLETIN DE TRAFICO CDMX

{greeting}

Te has suscrito exitosamente al Boletin de Trafico CDMX!

DETALLES DE TU SUSCRIPCION
Frecuencia: {freq_text}

QUE PUEDES ESPERAR?
- Reportes de incidentes de trafico en tiempo real
- Alertas de accidentes y cierres de vialidades
- Informacion sobre obras y manifestaciones
- Recomendaciones para optimizar tu ruta

Boletin de Trafico CDMX - Mantente informado sobre el trafico en la ciudad

Para cancelar tu suscripcion, responde a este email con "CANCELAR" y tu token: {unsubscribe_token}
"""
