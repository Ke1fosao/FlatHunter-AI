from __future__ import annotations

from uuid import UUID

from django.core.cache import cache
from django.shortcuts import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.analysis.market_services import refresh_listing_market_assessment
from apps.analysis.models import ListingMarketAssessment, ListingRiskAssessment
from apps.analysis.querysets import approved_listing_queryset
from apps.analysis.risk_services import refresh_listing_risk_assessment
from apps.analysis.serializers import (
    ListingAnalysisRefreshSerializer,
    ListingMarketAssessmentSerializer,
    ListingPriceHistorySerializer,
    ListingRiskAssessmentSerializer,
)
from apps.analysis.services import refresh_listing_analysis


def _listing(listing_id: UUID):
    return get_object_or_404(approved_listing_queryset(), pk=listing_id)


class ListingPriceHistoryView(APIView):
    def get(self, request: Request, listing_id: UUID) -> Response:
        listing = _listing(listing_id)
        events = listing.price_history.order_by("-changed_at", "-detected_at")
        return Response(
            {
                "listing_id": str(listing.id),
                "current_price_uah": listing.price_uah,
                "events": ListingPriceHistorySerializer(events, many=True).data,
            }
        )


class ListingMarketAnalysisView(APIView):
    def get(self, request: Request, listing_id: UUID) -> Response:
        listing = _listing(listing_id)
        assessment = ListingMarketAssessment.objects.filter(listing=listing).first()
        if assessment is None:
            assessment = refresh_listing_market_assessment(listing.id)
        return Response(
            {
                "listing_id": str(listing.id),
                "current_price_uah": listing.price_uah,
                "assessment": ListingMarketAssessmentSerializer(assessment).data,
            }
        )


class ListingRiskAnalysisView(APIView):
    def get(self, request: Request, listing_id: UUID) -> Response:
        listing = _listing(listing_id)
        assessment = ListingRiskAssessment.objects.filter(listing=listing).first()
        if assessment is None:
            market = ListingMarketAssessment.objects.filter(listing=listing).first()
            if market is None:
                market = refresh_listing_market_assessment(listing.id)
            assessment = refresh_listing_risk_assessment(listing.id, market=market)
        return Response(
            {
                "listing_id": str(listing.id),
                "assessment": ListingRiskAssessmentSerializer(assessment).data,
                "disclaimer": "Допоміжна оцінка, не юридичний висновок.",
            }
        )


class ListingAnalysisRefreshView(APIView):
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "analysis_refresh"

    def post(self, request: Request, listing_id: UUID) -> Response:
        listing = _listing(listing_id)
        serializer = ListingAnalysisRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        idempotency_key = request.headers.get("Idempotency-Key", "").strip()[:128]
        cache_key = ""
        if idempotency_key:
            cache_key = f"analysis-refresh:{request.user.pk}:{listing.id}:{idempotency_key}"
            cached = cache.get(cache_key)
            if isinstance(cached, dict):
                return Response(cached)

        result = refresh_listing_analysis(
            listing.id,
            force=bool(serializer.validated_data["force"]),
        )
        payload = {
            "listing_id": str(listing.id),
            "market": ListingMarketAssessmentSerializer(result.market).data,
            "risk": ListingRiskAssessmentSerializer(result.risk).data,
        }
        if cache_key:
            cache.set(cache_key, payload, timeout=300)
        return Response(payload)
