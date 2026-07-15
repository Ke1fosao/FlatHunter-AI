from django.urls import path

from apps.telegram_bot.views import telegram_status, telegram_webhook

urlpatterns = [
    path("webhook/", telegram_webhook, name="telegram-webhook"),
    path("status/", telegram_status, name="telegram-status"),
]
