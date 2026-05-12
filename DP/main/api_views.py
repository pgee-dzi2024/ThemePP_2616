from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .importers import parse_emails_from_csv
from .models import Campaign, Recipient, CampaignRecipient, EmailSendLog
from .serializers import (
    CampaignSerializer,
    CampaignDetailSerializer,
    CampaignCreateSerializer,
    RecipientImportSerializer,
    RecipientFileImportSerializer,
    CampaignActionSerializer,
)
from .worker import enqueue_campaign


def import_recipients_to_campaign(campaign, emails):
    created_count = 0
    skipped_count = 0

    with transaction.atomic():
        for email in emails:
            recipient, created = Recipient.objects.get_or_create(
                email=email,
                defaults={'is_valid': True, 'validation_error': ''}
            )

            if not created:
                recipient.is_valid = True
                recipient.validation_error = ''
                recipient.save(update_fields=['is_valid', 'validation_error'])

            _, rel_created = CampaignRecipient.objects.get_or_create(
                campaign=campaign,
                recipient=recipient,
                defaults={'status': CampaignRecipient.STATUS_PENDING}
            )

            if rel_created:
                created_count += 1
            else:
                skipped_count += 1

    return created_count, skipped_count


class CampaignListCreateAPIView(ListCreateAPIView):
    queryset = Campaign.objects.all().order_by('-created_at')
    serializer_class = CampaignSerializer

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CampaignCreateSerializer
        return CampaignSerializer

    def perform_create(self, serializer):
        serializer.save(status=Campaign.STATUS_DRAFT)


class CampaignDetailAPIView(RetrieveAPIView):
    queryset = Campaign.objects.all()
    serializer_class = CampaignDetailSerializer


class CampaignImportRecipientsAPIView(APIView):
    def post(self, request, pk):
        campaign = get_object_or_404(Campaign, pk=pk)

        serializer = RecipientImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        valid_emails = serializer.context.get('valid_emails', [])
        invalid_emails = serializer.context.get('invalid_emails', [])

        created_count, skipped_count = import_recipients_to_campaign(campaign, valid_emails)

        return Response(
            {
                'message': 'Получателите са импортирани успешно.',
                'campaign_id': campaign.id,
                'valid_emails_count': len(valid_emails),
                'invalid_emails_count': len(invalid_emails),
                'created_campaign_recipients': created_count,
                'existing_campaign_recipients': skipped_count,
                'invalid_emails': invalid_emails,
            },
            status=status.HTTP_201_CREATED
        )


class CampaignImportRecipientsFileAPIView(APIView):
    def post(self, request, pk):
        campaign = get_object_or_404(Campaign, pk=pk)

        serializer = RecipientFileImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data['file']

        if not uploaded_file.name.lower().endswith('.csv'):
            return Response(
                {'detail': 'Позволен е само CSV файл.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            parsed = parse_emails_from_csv(uploaded_file)
        except UnicodeDecodeError:
            return Response(
                {'detail': 'Файлът не може да бъде прочетен. Използвай UTF-8 или CP1251.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception:
            return Response(
                {'detail': 'Грешка при обработка на файла.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        valid_emails = parsed['valid_emails']
        invalid_entries = parsed['invalid_entries']

        if not valid_emails:
            return Response(
                {
                    'detail': 'Няма валидни имейл адреси във файла.',
                    'invalid_entries': invalid_entries,
                    'total_rows': parsed['total_rows'],
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        created_count, skipped_count = import_recipients_to_campaign(campaign, valid_emails)

        return Response(
            {
                'message': 'Файлът е обработен успешно.',
                'campaign_id': campaign.id,
                'total_rows': parsed['total_rows'],
                'valid_emails_count': len(valid_emails),
                'invalid_emails_count': len(invalid_entries),
                'created_campaign_recipients': created_count,
                'existing_campaign_recipients': skipped_count,
                'invalid_entries': invalid_entries,
            },
            status=status.HTTP_201_CREATED
        )


class CampaignStatsAPIView(APIView):
    def get(self, request, pk):
        campaign = get_object_or_404(Campaign, pk=pk)

        return Response(
            {
                'campaign_id': campaign.id,
                'status': campaign.status,
                'total_recipients': campaign.total_recipients,
                'sent_count': campaign.sent_count,
                'failed_count': campaign.failed_count,
                'pending_count': campaign.pending_count,
            },
            status=status.HTTP_200_OK
        )


class CampaignStartAPIView(APIView):
    def post(self, request, pk):
        campaign = get_object_or_404(Campaign, pk=pk)

        if campaign.status in [Campaign.STATUS_SENDING, Campaign.STATUS_COMPLETED]:
            return Response(
                {'detail': 'Кампанията вече е изпратена или се изпраща.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not campaign.campaign_recipients.exists():
            return Response(
                {'detail': 'Кампанията няма получатели.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        campaign.status = Campaign.STATUS_READY
        campaign.save(update_fields=['status'])
        enqueue_campaign(campaign.id)

        return Response(
            {
                'detail': 'Кампанията е поставена в опашката за изпращане.',
                'campaign_id': campaign.id,
                'status': campaign.status,
            },
            status=status.HTTP_200_OK
        )


class CampaignPauseAPIView(APIView):
    def post(self, request, pk):
        campaign = get_object_or_404(Campaign, pk=pk)

        if campaign.status != Campaign.STATUS_SENDING:
            return Response(
                {'detail': 'Само кампания, която се изпраща, може да бъде паузирана.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        campaign.status = Campaign.STATUS_PAUSED
        campaign.save(update_fields=['status'])

        return Response(
            {
                'detail': 'Кампанията е паузирана.',
                'campaign_id': campaign.id,
                'status': campaign.status,
            },
            status=status.HTTP_200_OK
        )


class CampaignStopAPIView(APIView):
    def post(self, request, pk):
        campaign = get_object_or_404(Campaign, pk=pk)

        if campaign.status == Campaign.STATUS_STOPPED:
            return Response(
                {'detail': 'Кампанията вече е спряна.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        campaign.status = Campaign.STATUS_STOPPED
        campaign.save(update_fields=['status'])

        return Response(
            {
                'detail': 'Кампанията е спряна.',
                'campaign_id': campaign.id,
                'status': campaign.status,
            },
            status=status.HTTP_200_OK
        )


class CampaignLogsAPIView(APIView):
    def get(self, request, pk):
        campaign = get_object_or_404(Campaign, pk=pk)

        logs = EmailSendLog.objects.filter(campaign=campaign).select_related('recipient').order_by('-created_at')

        return Response(
            {
                'campaign_id': campaign.id,
                'logs': [
                    {
                        'id': log.id,
                        'recipient': log.recipient.email,
                        'status': log.status,
                        'message': log.message,
                        'created_at': log.created_at,
                    }
                    for log in logs
                ],
            },
            status=status.HTTP_200_OK
        )