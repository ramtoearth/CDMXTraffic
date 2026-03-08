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
    unsubscribe_url = f"{landing_url}/unsubscribe?token={unsubscribe_token}"

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Bienvenido al Boletín de Tráfico CDMX</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f5f5f5;">
  <table role="presentation" style="width: 100%; border-collapse: collapse;">
    <tr>
      <td align="center" style="padding: 40px 20px;">
        <table role="presentation" style="max-width: 600px; width: 100%; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
          <!-- Header -->
          <tr>
            <td style="background: linear-gradient(135deg, #e63946 0%, #d62828 100%); padding: 40px 30px; text-align: center; border-radius: 8px 8px 0 0;">
              <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 700; letter-spacing: -0.5px;">
                🚦 Boletín de Tráfico CDMX
              </h1>
            </td>
          </tr>
          
          <!-- Main Content -->
          <tr>
            <td style="padding: 40px 30px;">
              <p style="margin: 0 0 20px; font-size: 18px; color: #1a1a1a; line-height: 1.6;">
                {greeting}
              </p>
              
              <p style="margin: 0 0 20px; font-size: 16px; color: #333333; line-height: 1.6;">
                ¡Te has suscrito exitosamente al <strong>Boletín de Tráfico CDMX</strong>! 🎉
              </p>
              
              <div style="background-color: #f8f9fa; border-left: 4px solid #e63946; padding: 20px; margin: 25px 0; border-radius: 4px;">
                <p style="margin: 0; font-size: 15px; color: #495057; line-height: 1.6;">
                  Recibirás actualizaciones de tráfico <strong style="color: #e63946;">{freq_text}</strong> en <strong>{email}</strong>
                </p>
              </div>
              
              <h2 style="margin: 30px 0 20px; font-size: 20px; color: #1a1a1a; font-weight: 600;">
                ¿Qué puedes esperar?
              </h2>
              
              <table role="presentation" style="width: 100%; margin: 20px 0;">
                <tr>
                  <td style="padding: 12px 0; vertical-align: top;">
                    <span style="color: #e63946; font-size: 20px; margin-right: 10px;">🚗</span>
                    <span style="font-size: 15px; color: #333333; line-height: 1.6;">Reportes de incidentes de tráfico en tiempo real</span>
                  </td>
                </tr>
                <tr>
                  <td style="padding: 12px 0; vertical-align: top;">
                    <span style="color: #e63946; font-size: 20px; margin-right: 10px;">⚠️</span>
                    <span style="font-size: 15px; color: #333333; line-height: 1.6;">Alertas de accidentes y cierres de vialidades</span>
                  </td>
                </tr>
                <tr>
                  <td style="padding: 12px 0; vertical-align: top;">
                    <span style="color: #e63946; font-size: 20px; margin-right: 10px;">🚧</span>
                    <span style="font-size: 15px; color: #333333; line-height: 1.6;">Información sobre obras y manifestaciones</span>
                  </td>
                </tr>
                <tr>
                  <td style="padding: 12px 0; vertical-align: top;">
                    <span style="color: #e63946; font-size: 20px; margin-right: 10px;">📍</span>
                    <span style="font-size: 15px; color: #333333; line-height: 1.6;">Recomendaciones para optimizar tu ruta</span>
                  </td>
                </tr>
              </table>
              
              <div style="text-align: center; margin: 35px 0 25px;">
                <a href="{landing_url}" style="display: inline-block; background-color: #e63946; color: #ffffff; text-decoration: none; padding: 14px 32px; border-radius: 6px; font-size: 16px; font-weight: 600; transition: background-color 0.3s;">
                  Visita Nuestra Página
                </a>
              </div>
            </td>
          </tr>
          
          <!-- Footer -->
          <tr>
            <td style="background-color: #f8f9fa; padding: 30px; text-align: center; border-radius: 0 0 8px 8px; border-top: 1px solid #e9ecef;">
              <p style="margin: 0 0 10px; font-size: 13px; color: #6c757d; line-height: 1.5;">
                Boletín de Tráfico CDMX - Mantente informado sobre el tráfico en la ciudad
              </p>
              <p style="margin: 10px 0 0; font-size: 12px; color: #868e96;">
                Si deseas cancelar tu suscripción, 
                <a href="{unsubscribe_url}" style="color: #e63946; text-decoration: underline;">haz clic aquí</a>
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
    unsubscribe_url = f"{landing_url}/unsubscribe?token={unsubscribe_token}"

    return f"""🚦 BOLETÍN DE TRÁFICO CDMX

{greeting}

¡Te has suscrito exitosamente al Boletín de Tráfico CDMX! 🎉

DETALLES DE TU SUSCRIPCIÓN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Frecuencia: {freq_text}
Email: {email}

¿QUÉ PUEDES ESPERAR?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚗 Reportes de incidentes de tráfico en tiempo real
⚠️  Alertas de accidentes y cierres de vialidades
🚧 Información sobre obras y manifestaciones
📍 Recomendaciones para optimizar tu ruta

VISITA NUESTRA PÁGINA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{landing_url}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Boletín de Tráfico CDMX - Mantente informado sobre el tráfico en la ciudad

Para cancelar tu suscripción, visita:
{unsubscribe_url}
"""
