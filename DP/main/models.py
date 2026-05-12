from django.db import models


class Campaign(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_READY = 'ready'
    STATUS_SENDING = 'sending'
    STATUS_PAUSED = 'paused'
    STATUS_STOPPED = 'stopped'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'

    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Чернова'),
        (STATUS_READY, 'Готова'),
        (STATUS_SENDING, 'Изпраща се'),
        (STATUS_PAUSED, 'Пауза'),
        (STATUS_STOPPED, 'Спряна'),
        (STATUS_COMPLETED, 'Завършена'),
        (STATUS_FAILED, 'Грешка'),
    ]

    CONTENT_TEXT = 'text'
    CONTENT_HTML = 'html'

    CONTENT_TYPE_CHOICES = [
        (CONTENT_TEXT, 'Текст'),
        (CONTENT_HTML, 'HTML'),
    ]

    name = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    content = models.TextField()
    content_type = models.CharField(
        max_length=10,
        choices=CONTENT_TYPE_CHOICES,
        default=CONTENT_TEXT
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def total_recipients(self):
        return self.campaign_recipients.count()

    @property
    def sent_count(self):
        return self.campaign_recipients.filter(status=CampaignRecipient.STATUS_SENT).count()

    @property
    def failed_count(self):
        return self.campaign_recipients.filter(status=CampaignRecipient.STATUS_FAILED).count()

    @property
    def pending_count(self):
        return self.campaign_recipients.filter(status=CampaignRecipient.STATUS_PENDING).count()


class Recipient(models.Model):
    email = models.EmailField(unique=True)
    is_valid = models.BooleanField(default=True)
    validation_error = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email


class CampaignRecipient(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_SENT = 'sent'
    STATUS_FAILED = 'failed'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Чака'),
        (STATUS_SENT, 'Изпратено'),
        (STATUS_FAILED, 'Неуспешно'),
    ]

    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name='campaign_recipients'
    )
    recipient = models.ForeignKey(
        Recipient,
        on_delete=models.CASCADE,
        related_name='recipient_campaigns'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True, default='')
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('campaign', 'recipient')

    def __str__(self):
        return f'{self.campaign.name} -> {self.recipient.email}'


class EmailSendLog(models.Model):
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name='send_logs'
    )
    recipient = models.ForeignKey(
        Recipient,
        on_delete=models.CASCADE,
        related_name='send_logs'
    )
    status = models.CharField(max_length=20)
    message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.campaign.name} / {self.recipient.email} / {self.status}'