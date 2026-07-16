from __future__ import annotations

from typing import Any, cast

from django.db.models import QuerySet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.duplicates.presentation import cluster_aware_listing_queryset
from apps.listings.models import Listing
from apps.listings.serializers import ListingSerializer
from apps.matching.engine import evaluate_match
from apps.searches.models import SearchProfile
from apps.searches.parser import parse_search_text
from apps.searches.serializers import (
    MatchQuerySerializer,
    NaturalLanguageSearchSerializer,
    SearchProfileSerializer,
)


class SearchProfileViewSet(viewsets.ModelViewSet):
    serializer_class = SearchProfileSerializer

    def get_queryset(self) -> QuerySet[SearchProfile]:
        user = cast(User, self.request.user)
        return SearchProfile.objects.filter(user=user).prefetch_related(
            "important_places",
            "notification_preference",
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

    @action(detail=True, methods=["get"])
    def matches(self, request: Request, pk: str | None = None) -> Response:
        profile = self.get_object()
        query = MatchQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        params = query.validated_data
        user = cast(User, request.user)
        base = Listing.objects.filter(
            is_active=True,
            source__enabled=True,
            source__legal_status__in=("approved_demo", "approved"),
        )
        listings = list(
            cluster_aware_listing_queryset(base, user=user).order_by("-published_at")[:1000]
        )
        matched: list[dict[str, Any]] = []
        for listing in listings:
            evaluation = evaluate_match(profile, listing)
            if params["eligible_only"] and not evaluation.eligible:
                continue
            if evaluation.score < params["min_score"]:
                continue
            matched.append(
                {
                    "listing": ListingSerializer(listing, context={"request": request}).data,
                    "match": evaluation.to_dict(),
                }
            )

        ordering = params["ordering"]
        if ordering == "-match_score":
            matched.sort(key=lambda item: item["match"]["score"], reverse=True)
        elif ordering == "match_score":
            matched.sort(key=lambda item: item["match"]["score"])
        elif ordering == "price_uah":
            matched.sort(key=lambda item: item["listing"]["price_min_uah"])
        else:
            matched.sort(key=lambda item: item["listing"]["published_at"], reverse=True)

        limited = matched[: params["limit"]]
        return Response(
            {
                "profile": {
                    "id": str(profile.id),
                    "name": profile.name,
                    "city": profile.city,
                },
                "count": len(matched),
                "results": limited,
                "meta": {
                    "algorithm": "deterministic-v1-cluster-aware",
                    "min_score": params["min_score"],
                    "eligible_only": params["eligible_only"],
                    "ordering": ordering,
                },
            }
        )


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
