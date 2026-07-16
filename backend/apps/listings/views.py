from __future__ import annotations

from django.db.models import QuerySet
from rest_framework import filters, viewsets

from apps.listings.models import Listing
from apps.listings.serializers import ListingFilterSerializer, ListingSerializer


class ListingViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ListingSerializer
    filter_backends = (filters.OrderingFilter, filters.SearchFilter)
    search_fields = ("title", "description", "city", "district", "street")
    ordering_fields = ("published_at", "price_uah", "rooms", "total_area")
    ordering = ("-published_at",)

    def get_queryset(self) -> QuerySet[Listing]:
        filters_serializer = ListingFilterSerializer(data=self.request.query_params)
        filters_serializer.is_valid(raise_exception=True)
        params = filters_serializer.validated_data

        queryset = Listing.objects.filter(
            is_active=True,
            source__enabled=True,
            source__legal_status__in=("approved_demo", "approved"),
        ).select_related("source")

        city = params.get("city")
        district = params.get("district")
        rooms = params.get("rooms")
        price_min = params.get("price_min")
        price_max = params.get("price_max")

        if city:
            queryset = queryset.filter(city__iexact=city)
        if district:
            queryset = queryset.filter(district__iexact=district)
        if rooms is not None:
            queryset = queryset.filter(rooms=rooms)
        if price_min is not None:
            queryset = queryset.filter(price_uah__gte=price_min)
        if price_max is not None:
            queryset = queryset.filter(price_uah__lte=price_max)
        return queryset
