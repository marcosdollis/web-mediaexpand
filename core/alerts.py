"""
Serviço de alerta de desconexão de dispositivos TV.
Envia e-mail via Brevo (SMTP) quando um dispositivo fica offline.
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


# ─── helpers ────────────────────────────────────────────────────────────────

def _get_destinatarios(dispositivo) -> list[str]:
    """
    Monta a lista de e-mails que devem receber o alerta.
    Inclui: franqueado direto do dispositivo + franqueado do município + todos os OWNERs.
    """
    from core.models import User
    emails: set[str] = set()

    # franqueado diretamente atribuído ao dispositivo
    if dispositivo.franqueado_id and dispositivo.franqueado.email:
        emails.add(dispositivo.franqueado.email)

    # franqueado do município
    try:
        if dispositivo.municipio.franqueado_id and dispositivo.municipio.franqueado.email:
            emails.add(dispositivo.municipio.franqueado.email)
    except Exception:
        pass

    # todos os OWNERs sempre recebem
    for owner in User.objects.filter(role='OWNER', is_active=True).exclude(email=''):
        emails.add(owner.email)

    return list(emails)


def _send_smtp(subject: str, html_body: str, destinatarios: list[str]) -> bool:
    """Envia e-mail via Brevo SMTP. Retorna True em sucesso."""
    if not destinatarios:
        logger.warning("alerts: nenhum destinatário para o alerta, e-mail não enviado.")
        return False

    smtp_host = getattr(settings, 'EMAIL_HOST', 'smtp-relay.brevo.com')
    smtp_port = getattr(settings, 'EMAIL_PORT', 587)
    smtp_user = getattr(settings, 'EMAIL_HOST_USER', '')
    smtp_pass = getattr(settings, 'EMAIL_HOST_PASSWORD', '')
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', smtp_user)

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = ', '.join(destinatarios)
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, destinatarios, msg.as_string())
        logger.info("alerts: e-mail '%s' enviado para %s", subject, destinatarios)
        return True
    except Exception as exc:
        logger.error("alerts: falha ao enviar e-mail: %s", exc)
        return False


# ─── templates HTML ─────────────────────────────────────────────────────────

def _html_offline(dispositivo, ultima_vez: str) -> str:
    return f"""
<html><body style="font-family:sans-serif;background:#0a0e1a;color:#f4f6ff;padding:32px">
<div style="max-width:520px;margin:0 auto;background:#111827;border-radius:12px;
            border:1px solid #ff4444;padding:28px">
  <p style="font-size:11px;text-transform:uppercase;letter-spacing:2px;
             color:#ff6666;margin:0 0 12px">⚠️ Alerta de Desconexão</p>
  <h2 style="margin:0 0 8px;font-size:20px;color:#fff">Dispositivo offline</h2>
  <p style="color:#8892b0;margin:0 0 20px;font-size:14px">
    Um dispositivo da rede Vitrine Digital ficou offline.
  </p>
  <table style="width:100%;border-collapse:collapse;font-size:13px">
    <tr>
      <td style="padding:8px 12px;color:#8892b0;white-space:nowrap">Dispositivo</td>
      <td style="padding:8px 12px;color:#fff;font-weight:600">{dispositivo.nome}</td>
    </tr>
    <tr style="background:rgba(255,255,255,0.04)">
      <td style="padding:8px 12px;color:#8892b0">Município</td>
      <td style="padding:8px 12px;color:#fff">{dispositivo.municipio}</td>
    </tr>
    <tr>
      <td style="padding:8px 12px;color:#8892b0">Localização</td>
      <td style="padding:8px 12px;color:#fff">{dispositivo.localizacao or '—'}</td>
    </tr>
    <tr style="background:rgba(255,255,255,0.04)">
      <td style="padding:8px 12px;color:#8892b0">Último contato</td>
      <td style="padding:8px 12px;color:#ff9966">{ultima_vez}</td>
    </tr>
    <tr>
      <td style="padding:8px 12px;color:#8892b0">Versão app</td>
      <td style="padding:8px 12px;color:#fff">{dispositivo.versao_app or '—'}</td>
    </tr>
    <tr style="background:rgba(255,255,255,0.04)">
      <td style="padding:8px 12px;color:#8892b0">ID único</td>
      <td style="padding:8px 12px;color:#8892b0;font-size:11px">{dispositivo.identificador_unico}</td>
    </tr>
  </table>
  <p style="margin:20px 0 0;font-size:12px;color:#8892b0">
    Verifique a conexão de rede e energia do dispositivo.<br>
    Este alerta não será repetido até que o dispositivo se reconecte.
  </p>
</div>
</body></html>
"""


def _html_online(dispositivo) -> str:
    reconectado_em = timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M')
    return f"""
<html><body style="font-family:sans-serif;background:#0a0e1a;color:#f4f6ff;padding:32px">
<div style="max-width:520px;margin:0 auto;background:#111827;border-radius:12px;
            border:1px solid #00d4ff;padding:28px">
  <p style="font-size:11px;text-transform:uppercase;letter-spacing:2px;
             color:#00d4ff;margin:0 0 12px">✅ Dispositivo reconectado</p>
  <h2 style="margin:0 0 8px;font-size:20px;color:#fff">Dispositivo voltou online</h2>
  <p style="color:#8892b0;margin:0 0 20px;font-size:14px">
    O dispositivo que estava offline retomou a conexão.
  </p>
  <table style="width:100%;border-collapse:collapse;font-size:13px">
    <tr>
      <td style="padding:8px 12px;color:#8892b0">Dispositivo</td>
      <td style="padding:8px 12px;color:#fff;font-weight:600">{dispositivo.nome}</td>
    </tr>
    <tr style="background:rgba(255,255,255,0.04)">
      <td style="padding:8px 12px;color:#8892b0">Município</td>
      <td style="padding:8px 12px;color:#fff">{dispositivo.municipio}</td>
    </tr>
    <tr>
      <td style="padding:8px 12px;color:#8892b0">Reconectado em</td>
      <td style="padding:8px 12px;color:#00d4ff">{reconectado_em}</td>
    </tr>
  </table>
</div>
</body></html>
"""


# ─── funções públicas ────────────────────────────────────────────────────────

def send_offline_alert(dispositivo) -> bool:
    """Envia alerta de offline. Deve ser chamada apenas uma vez por incidente."""
    ultima = dispositivo.ultima_sincronizacao
    if ultima:
        ultima_vez = timezone.localtime(ultima).strftime('%d/%m/%Y %H:%M:%S')
    else:
        ultima_vez = 'nunca'

    destinatarios = _get_destinatarios(dispositivo)
    subject = f"⚠️ TV OFFLINE: {dispositivo.nome} ({dispositivo.municipio})"
    return _send_smtp(subject, _html_offline(dispositivo, ultima_vez), destinatarios)


def send_online_alert(dispositivo) -> bool:
    """Envia notificação de reconexão. Chamada quando dispositivo estava com alerta ativo e voltou."""
    destinatarios = _get_destinatarios(dispositivo)
    subject = f"✅ TV ONLINE: {dispositivo.nome} ({dispositivo.municipio})"
    return _send_smtp(subject, _html_online(dispositivo), destinatarios)


def check_offline_devices():
    """
    Verifica dispositivos ativos que não enviaram heartbeat dentro do threshold.
    Envia e-mail de alerta (uma vez por incidente de desconexão).
    Chamada pelo scheduler a cada minuto.
    """
    from core.models import DispositivoTV

    threshold = getattr(settings, 'DEVICE_OFFLINE_THRESHOLD_MINUTES', 10)
    cutoff = timezone.now() - timezone.timedelta(minutes=threshold)

    # Dispositivos que deveriam estar online mas não aparecem
    offline_candidates = DispositivoTV.objects.filter(
        ativo=True,
        alerta_desconexao_enviado=False,
        ultima_sincronizacao__isnull=False,
        ultima_sincronizacao__lt=cutoff,
    ).select_related('municipio', 'municipio__franqueado', 'franqueado')

    alerted = 0
    for dispositivo in offline_candidates:
        try:
            ok = send_offline_alert(dispositivo)
            if ok:
                dispositivo.alerta_desconexao_enviado = True
                dispositivo.save(update_fields=['alerta_desconexao_enviado'])
                alerted += 1
        except Exception as exc:
            logger.error("alerts: erro ao processar dispositivo %s: %s", dispositivo.id, exc)

    if alerted:
        logger.info("alerts: %d dispositivo(s) marcado(s) como offline e alertados.", alerted)

    return alerted
