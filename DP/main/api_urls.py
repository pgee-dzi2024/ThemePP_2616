from django.urls import path

from .api_views import (
    CampaignListCreateAPIView,
    CampaignDetailAPIView,
    CampaignImportRecipientsAPIView,
    CampaignImportRecipientsFileAPIView,
    CampaignStatsAPIView,
    CampaignStartAPIView,
    CampaignStopAPIView,
    CampaignPauseAPIView,
    CampaignLogsAPIView,
)

urlpatterns = [
    path('campaigns/', CampaignListCreateAPIView.as_view(), name='api-campaign-list-create'),
    path('campaigns/<int:pk>/', CampaignDetailAPIView.as_view(), name='api-campaign-detail'),
    path('campaigns/<int:pk>/import-recipients/', CampaignImportRecipientsAPIView.as_view(), name='api-campaign-import-recipients'),
    path('campaigns/<int:pk>/import-recipients-file/', CampaignImportRecipientsFileAPIView.as_view(), name='api-campaign-import-recipients-file'),
    path('campaigns/<int:pk>/stats/', CampaignStatsAPIView.as_view(), name='api-campaign-stats'),
    path('campaigns/<int:pk>/start/', CampaignStartAPIView.as_view(), name='api-campaign-start'),
    path('campaigns/<int:pk>/stop/', CampaignStopAPIView.as_view(), name='api-campaign-stop'),
    path('campaigns/<int:pk>/pause/', CampaignPauseAPIView.as_view(), name='api-campaign-pause'),
    path('campaigns/<int:pk>/logs/', CampaignLogsAPIView.as_view(), name='api-campaign-logs'),
]