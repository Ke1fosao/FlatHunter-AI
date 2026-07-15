from django.urls import path

from apps.accounts.views import LogoutView, MeView, TelegramAuthView

urlpatterns = [
    path("auth/telegram/", TelegramAuthView.as_view(), name="telegram-auth"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
]
