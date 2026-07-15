from __future__ import annotations

from typing import Any, cast

from django.db.models import QuerySet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.searches.models import SearchProfile
from apps.searches.parser import parse_search_text
from apps.searches.serializers import NaturalLanguageSearchSerializer, SearchProfileSerializer


class SearchProfileViewSet(viewsets.ModelViewSet):
    serializer_class = SearchProfileSerializer

    def get_queryset(self) -> QuerySet[SearchProfile]:
        user = cast(User, self.request.user)
        return SearchProfile.objects.filter(user=user).prefetch_related(
            "important_places", "notification_preference"
        )

    @action(detail=True, methods=["post"])
    def activate(self, request: Request, pk: str | None = None) -> Response:
        profile = self.get_object()
        profile.is_active = True
        profile.save(update_fields=("is_active", "updated_at"))
        return Response(self.get_serializer(profile).data)

    @action(detail=True, methods=["post"])
    def pause(self, request: Request, pk: str | None = None) -> Response:
        profile = self.get_object()
        profile.is_active = False
        profile.save(update_fields=("is_active", "updated_at"))
        return Response(self.get_serializer(profile).data)


class ParseNaturalLanguageView(APIView):
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = NaturalLanguageSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        parsed = parse_search_text(serializer.validated_data["text"])
        return Response(
            {
                "data": parsed.data,
                "confidence": parsed.confidence,
                "missing_fields": parsed.missing_fields,
            },
            status=status.HTTP_200_OK,
        )
