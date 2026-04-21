import smtplib
import time

from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

from .models import Campaign, CampaignRecipient, EmailSendLog


def validate_smtp_configuration():
    required_settings = [
        getattr(settings, 'EMAIL_HOST', ''),
        getattr(settings, 'EMAIL_PORT', ''),
        getattr(settings, 'EMAIL_HOST_USER', ''),
        getattr(settings, 'EMAIL_HOST_PASSWORD', ''),
    ]

    if not all(required_settings):
        return False, 'Липсва SMTP конфигурация.'

    return True, ''


def send_campaign_email(campaign, recipient_email):
    """
    Връща:
    (success: bool, error_message: str, is_temporary_error: bool)
    """
    is_valid, error = validate_smtp_configuration()
    if not is_valid:
        return False, error, False

    try:
        message = EmailMessage(
            subject=campaign.subject,
            body=campaign.content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
        )

        if campaign.content_type == Campaign.CONTENT_HTML:
            message.content_subtype = 'html'

        message.send(fail_silently=False)
        return True, '', False

    except smtplib.SMTPRecipientsRefused:
        return False, 'Невалиден или отхвърлен получател.', False
    except smtplib.SMTPAuthenticationError:
        return False, 'Грешка при SMTP автентикация.', False
    except smtplib.SMTPServerDisconnected:
        return False, 'SMTP сървърът е прекъснал връзката.', True
    except smtplib.SMTPConnectError:
        return False, 'Не може да се осъществи връзка със SMTP сървъра.', True
    except smtplib.SMTPDataError:
        return False, 'SMTP сървърът върна грешка при данните.', True
    except smtplib.SMTPException as exc:
        return False, f'SMTP грешка: {str(exc)}', True
    except Exception as exc:
        return False, f'Неочаквана грешка: {str(exc)}', False


def process_campaign_recipient(campaign_recipient):
    campaign = campaign_recipient.campaign
    recipient = campaign_recipient.recipient

    max_attempts = getattr(settings, 'EMAIL_MAX_RETRY_ATTEMPTS', 3)
    retry_delay = getattr(settings, 'EMAIL_RETRY_DELAY_SECONDS', 2)

    last_error = ''

    for attempt in range(1, max_attempts + 1):
        campaign_recipient.attempts = attempt
        campaign_recipient.status = CampaignRecipient.STATUS_PENDING
        campaign_recipient.last_error = ''
        campaign_recipient.save(update_fields=['attempts', 'status', 'last_error'])

        success, error_message, temporary_error = send_campaign_email(campaign, recipient.email)

        if success:
            campaign_recipient.status = CampaignRecipient.STATUS_SENT
            campaign_recipient.last_error = ''
            campaign_recipient.sent_at = timezone.now()
            campaign_recipient.save(update_fields=['status', 'last_error', 'sent_at'])

            EmailSendLog.objects.create(
                campaign=campaign,
                recipient=recipient,
                status='sent',
                message='Имейлът е изпратен успешно.'
            )
            return

        last_error = error_message
        campaign_recipient.last_error = error_message
        campaign_recipient.save(update_fields=['last_error'])

        EmailSendLog.objects.create(
            campaign=campaign,
            recipient=recipient,
            status='retry' if temporary_error and attempt < max_attempts else 'failed',
            message=f'Опит {attempt}: {error_message}'
        )

        if not temporary_error:
            break

        if attempt < max_attempts:
            time.sleep(retry_delay)

    campaign_recipient.status = CampaignRecipient.STATUS_FAILED
    campaign_recipient.last_error = last_error
    campaign_recipient.save(update_fields=['status', 'last_error'])

    EmailSendLog.objects.create(
        campaign=campaign,
        recipient=recipient,
        status='failed',
        message=last_error
    )