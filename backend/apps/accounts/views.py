from __future__ import annotations

from typing import cast

from django.conf import settings
from django.contrib.auth import login, logout
from django.middleware.csrf import get_token
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.serializers import TelegramAuthSerializer
from apps.accounts.services import get_or_create_telegram_user
from apps.accounts.telegram import TelegramInitDataError, TelegramInitDataValidator


def _serialize_user(user: User) -> dict[str, object]:
    profile = user.telegram_profile
    return {
        "id": str(user.pk),
        "telegramId": profile.telegram_id,
        "firstName": user.first_name,
        "lastName": user.last_name,
        "username": profile.username,
        "locale": user.locale,
        "role": user.role,
    }


class TelegramAuthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list[type] = []

    @extend_schema(request=TelegramAuthSerializer, responses={200: dict})
    def post(self, request: Request) -> Response:
        serializer = TelegramAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validator = TelegramInitDataValidator(
            settings.TELEGRAM_BOT_TOKEN,
            max_age_seconds=settings.TELEGRAM_AUTH_MAX_AGE,
        )
        try:
            validated = validator.validate(serializer.validated_data["initData"])
        except TelegramInitDataError as exc:
            return Response(
                {"error": {"code": "invalid_telegram_data", "message": str(exc)}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user = get_or_create_telegram_user(validated.user)
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return Response({"user": _serialize_user(user), "csrfToken": get_token(request)})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return Response({"user": _serialize_user(cast(User, request.user))})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)
