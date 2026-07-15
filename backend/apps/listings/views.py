from __future__ import annotations

from django.db.models import QuerySet
from rest_framework import filters, viewsets

from apps.listings.models import Listing
from apps.listings.serializers import ListingSerializer


class ListingViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ListingSerializer
    filter_backends = (filters.OrderingFilter, filters.SearchFilter)
    search_fields = ("title", "description", "city", "district", "street")
    ordering_fields = ("published_at", "price_uah", "rooms", "total_area")
    ordering = ("-published_at",)

    def get_queryset(self) -> QuerySet[Listing]:
        queryset = Listing.objects.filter(is_active=True).select_related("source")
        city = self.request.query_params.get("city")
        rooms = self.request.query_params.get("rooms")
        price_min = self.request.query_params.get("price_min")
        price_max = self.request.query_params.get("price_max")
        district = self.request.query_params.get("district")
        if city:
            queryset = queryset.filter(city__iexact=city)
        if rooms and rooms.isdigit():
            queryset = queryset.filter(rooms=int(rooms))
        if price_min and price_min.isdigit():
            queryset = queryset.filter(price_uah__gte=int(price_min))
        if price_max and price_max.isdigit():
            queryset = queryset.filter(price_uah__lte=int(price_max))
        if district:
            queryset = queryset.filter(district__iexact=district)
        return queryset
