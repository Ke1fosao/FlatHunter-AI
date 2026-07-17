from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.ai_analysis.serializers import (
    ListingAIRequestSerializer,
    ListingComparisonRequestSerializer,
)
from apps.ai_analysis.services import (
    compare_listings_with_ai,
    owner_questions_with_ai,
    summarize_listing_with_ai,
)
from apps.listings.models import Listing
from apps.searches.models import SearchProfile


def _approved_listing_queryset() -> QuerySet[Listing]:
    return Listing.objects.filter(
        is_active=True,
        source__enabled=True,
        source__legal_status__in=("approved_demo", "approved"),
    ).select_related("source")


def _owned_profile(request: Request, profile_id: UUID | None) -> SearchProfile | None:
    if profile_id is None:
        return None
    user = cast(User, request.user)
    return get_object_or_404(SearchProfile, pk=profile_id, user=user)


class ListingSummaryView(APIView):
    def post(self, request: Request, listing_id: str, *args: Any, **kwargs: Any) -> Response:
        listing = get_object_or_404(_approved_listing_queryset(), pk=listing_id)
        result = summarize_listing_with_ai(listing, user=cast(User, request.user))
        return Response({**result.payload, "meta": result.meta}, status=status.HTTP_200_OK)


class ListingOwnerQuestionsView(APIView):
    def post(self, request: Request, listing_id: str, *args: Any, **kwargs: Any) -> Response:
        serializer = ListingAIRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = _owned_profile(request, serializer.validated_data.get("search_profile_id"))
        listing = get_object_or_404(_approved_listing_queryset(), pk=listing_id)
        result = owner_questions_with_ai(
            listing,
            user=cast(User, request.user),
            profile=profile,
        )
        return Response({**result.payload, "meta": result.meta}, status=status.HTTP_200_OK)


class ListingComparisonView(APIView):
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = ListingComparisonRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        listing_ids = serializer.validated_data["listing_ids"]
        profile = _owned_profile(request, serializer.validated_data.get("search_profile_id"))
        listings = list(_approved_listing_queryset().filter(pk__in=listing_ids))
        if len(listings) != len(listing_ids):
            return Response(
                {
                    "error": {
                        "code": "listing_not_found",
                        "message": "One or more listings are unavailable.",
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        listing_order = {str(item): index for index, item in enumerate(listing_ids)}
        listings.sort(key=lambda listing: listing_order[str(listing.id)])
        result = compare_listings_with_ai(
            listings,
            user=cast(User, request.user),
            profile=profile,
        )
        return Response({**result.payload, "meta": result.meta}, status=status.HTTP_200_OK)
