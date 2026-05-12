from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from .views import index, campaign_create_page, campaign_detail_page

urlpatterns = [
    path('', index, name='home'),
    path('campaigns/new/', campaign_create_page, name='campaign-create-page'),
    path('campaigns/<int:pk>/', campaign_detail_page, name='campaign-detail-page'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
