from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from rest_framework import serializers

from .models import Campaign, Recipient, CampaignRecipient, EmailSendLog


class RecipientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipient
        fields = ['id', 'email', 'is_valid', 'validation_error', 'created_at']
        read_only_fields = ['id', 'is_valid', 'validation_error', 'created_at']


class CampaignSerializer(serializers.ModelSerializer):
    total_recipients = serializers.IntegerField(read_only=True)
    sent_count = serializers.IntegerField(read_only=True)
    failed_count = serializers.IntegerField(read_only=True)
    pending_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Campaign
        fields = [
            'id',
            'name',
            'subject',
            'content',
            'content_type',
            'status',
            'created_at',
            'updated_at',
            'total_recipients',
            'sent_count',
            'failed_count',
            'pending_count',
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at', 'total_recipients', 'sent_count', 'failed_count', 'pending_count']


class CampaignDetailSerializer(serializers.ModelSerializer):
    total_recipients = serializers.IntegerField(read_only=True)
    sent_count = serializers.IntegerField(read_only=True)
    failed_count = serializers.IntegerField(read_only=True)
    pending_count = serializers.IntegerField(read_only=True)
    recipients = serializers.SerializerMethodField()
    logs = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = [
            'id',
            'name',
            'subject',
            'content',
            'content_type',
            'status',
            'created_at',
            'updated_at',
            'total_recipients',
            'sent_count',
            'failed_count',
            'pending_count',
            'recipients',
            'logs',
        ]
        read_only_fields = fields

    def get_recipients(self, obj):
        items = obj.campaign_recipients.select_related('recipient').all().order_by('id')
        return [
            {
                'id': item.id,
                'email': item.recipient.email,
                'status': item.status,
                'attempts': item.attempts,
                'last_error': item.last_error,
                'sent_at': item.sent_at,
            }
            for item in items
        ]

    def get_logs(self, obj):
        items = obj.send_logs.select_related('recipient').all().order_by('-created_at')
        return [
            {
                'id': log.id,
                'recipient': log.recipient.email,
                'status': log.status,
                'message': log.message,
                'created_at': log.created_at,
            }
            for log in items
        ]


class CampaignCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campaign
        fields = ['id', 'name', 'subject', 'content', 'content_type']
        read_only_fields = ['id']


class RecipientImportSerializer(serializers.Serializer):
    emails = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False
    )

    def validate_emails(self, value):
        normalized = []
        errors = []

        for raw_email in value:
            email = raw_email.strip()
            if not email:
                errors.append({'email': raw_email, 'error': 'Празен запис'})
                continue

            try:
                validate_email(email)
                normalized.append(email.lower())
            except ValidationError:
                errors.append({'email': raw_email, 'error': 'Невалиден имейл адрес'})

        if not normalized:
            raise serializers.ValidationError('Няма валидни имейл адреси.')

        self.context['valid_emails'] = normalized
        self.context['invalid_emails'] = errors
        return value


class RecipientFileImportSerializer(serializers.Serializer):
    file = serializers.FileField()


class CampaignActionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default='')