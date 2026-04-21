import threading
from queue import Queue, Empty

from django.db import close_old_connections

from .models import Campaign, CampaignRecipient
from .services import process_campaign_recipient


campaign_queue = Queue()
worker_thread = None
worker_running = False
worker_lock = threading.Lock()


def campaign_worker():
    global worker_running

    while worker_running:
        try:
            campaign_id = campaign_queue.get(timeout=1)
        except Empty:
            continue

        try:
            close_old_connections()

            try:
                campaign = Campaign.objects.get(id=campaign_id)
            except Campaign.DoesNotExist:
                continue

            if campaign.status == Campaign.STATUS_STOPPED:
                continue

            campaign.status = Campaign.STATUS_SENDING
            campaign.save(update_fields=['status'])

            recipients = CampaignRecipient.objects.select_related('recipient').filter(
                campaign=campaign,
                status=CampaignRecipient.STATUS_PENDING
            ).order_by('id')

            for campaign_recipient in recipients:
                campaign.refresh_from_db()

                if campaign.status in [Campaign.STATUS_STOPPED, Campaign.STATUS_PAUSED]:
                    break

                try:
                    process_campaign_recipient(campaign_recipient)
                except Exception as exc:
                    campaign_recipient.status = CampaignRecipient.STATUS_FAILED
                    campaign_recipient.last_error = str(exc)
                    campaign_recipient.save(update_fields=['status', 'last_error'])

            campaign.refresh_from_db()
            remaining = campaign.campaign_recipients.filter(
                status=CampaignRecipient.STATUS_PENDING
            ).exists()

            if campaign.status not in [Campaign.STATUS_STOPPED, Campaign.STATUS_PAUSED]:
                campaign.status = Campaign.STATUS_FAILED if remaining else Campaign.STATUS_COMPLETED
                campaign.save(update_fields=['status'])

        except Exception:
            pass
        finally:
            campaign_queue.task_done()


def start_worker():
    global worker_thread, worker_running

    with worker_lock:
        if worker_thread and worker_thread.is_alive():
            return

        worker_running = True
        worker_thread = threading.Thread(target=campaign_worker, daemon=True)
        worker_thread.start()


def stop_worker():
    global worker_running
    worker_running = False


def enqueue_campaign(campaign_id):
    campaign_queue.put(campaign_id)
    start_worker()