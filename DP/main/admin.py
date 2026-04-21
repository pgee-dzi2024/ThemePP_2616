from django.contrib import admin
from .models import Campaign, Recipient, CampaignRecipient, EmailSendLog


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'subject', 'content_type', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'content_type', 'created_at')
    search_fields = ('name', 'subject')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Recipient)
class RecipientAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'is_valid', 'validation_error', 'created_at')
    list_filter = ('is_valid', 'created_at')
    search_fields = ('email',)
    readonly_fields = ('created_at',)


@admin.register(CampaignRecipient)
class CampaignRecipientAdmin(admin.ModelAdmin):
    list_display = ('id', 'campaign', 'recipient', 'status', 'attempts', 'sent_at', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('campaign__name', 'recipient__email')
    readonly_fields = ('created_at', 'sent_at')


@admin.register(EmailSendLog)
class EmailSendLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'campaign', 'recipient', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('campaign__name', 'recipient__email')
    readonly_fields = ('created_at',)