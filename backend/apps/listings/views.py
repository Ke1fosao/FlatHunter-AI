from __future__ import annotations

from typing import Any, cast

from django.db import transaction
from django.db.models import Count, Prefetch, QuerySet
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.accounts.models import User
from apps.listings.models import Listing, UserListingState
from apps.listings.serializers import (
    ListingFilterSerializer,
    ListingSerializer,
    ListingStateMutationSerializer,
)
from apps.searches.models import SearchProfile


class ListingViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ListingSerializer
    filter_backends = (filters.OrderingFilter, filters.SearchFilter)
    search_fields = ("title", "description", "city", "district", "street")
    ordering_fields = ("published_at", "price_uah", "rooms", "total_area")
    ordering = ("-published_at",)

    def get_queryset(self) -> QuerySet[Listing]:
        user = cast(User, self.request.user)
        filters_serializer = ListingFilterSerializer(data=self.request.query_params)
        filters_serializer.is_valid(raise_exception=True)
        params = filters_serializer.validated_data

        state_queryset = UserListingState.objects.filter(user=user)
        queryset = (
            Listing.objects.filter(
                is_active=True,
                source__enabled=True,
                source__legal_status__in=("approved_demo", "approved"),
            )
            .select_related("source")
            .prefetch_related(
                Prefetch("user_states", queryset=state_queryset, to_attr="current_user_states")
            )
        )

        city = params.get("city")
        district = params.get("district")
        rooms = params.get("rooms")
        price_min = params.get("price_min")
        price_max = params.get("price_max")
        favorites = params.get("favorites")
        compared = params.get("compared")
        include_hidden = params.get("include_hidden", False)

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
        if favorites is not None:
            queryset = queryset.filter(user_states__user=user, user_states__is_favorite=favorites)
        if compared is not None:
            queryset = queryset.filter(user_states__user=user, user_states__is_compared=compared)
        if not include_hidden:
            queryset = queryset.exclude(user_states__user=user, user_states__is_hidden=True)
        return queryset.distinct()

    def get_serializer(self, *args: Any, **kwargs: Any) -> ListingSerializer:
        instances = args[0] if args else kwargs.get("instance")
        values = instances if isinstance(instances, list) else [instances]
        for instance in values:
            if isinstance(instance, Listing):
                states = getattr(instance, "current_user_states", [])
                instance.current_user_state = states[0] if states else None
        return super().get_serializer(*args, **kwargs)

    @action(detail=False, methods=["get"])
    def dashboard(self, request: Request) -> Response:
        user = cast(User, request.user)
        state_counts = UserListingState.objects.filter(user=user).aggregate(
            favorites=Count("id", filter=models.Q(is_favorite=True)),
            hidden=Count("id", filter=models.Q(is_hidden=True)),
            compared=Count("id", filter=models.Q(is_compared=True)),
        )
        active_profiles = SearchProfile.objects.filter(user=user, is_active=True).count()
        available = Listing.objects.filter(
            is_active=True,
            source__enabled=True,
            source__legal_status__in=("approved_demo", "approved"),
        ).count()
        recent = list(self.get_queryset()[:4])
        return Response(
            {
                "stats": {
                    "active_profiles": active_profiles,
                    "available_listings": available,
                    **state_counts,
                },
                "recent": ListingSerializer(recent, many=True, context={"request": request}).data,
            }
        )

    def _set_state(self, request: Request, field: str) -> Response:
        serializer = ListingStateMutationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        value = serializer.validated_data["value"]
        user = cast(User, request.user)
        listing = self.get_object()
        if field == "is_compared" and value:
            compared_count = UserListingState.objects.filter(user=user, is_compared=True).exclude(
                listing=listing
            ).count()
            if compared_count >= 4:
                return Response(
                    {"error": {"code": "comparison_limit", "message": "Можна порівнювати до 4 квартир."}},
                    status=status.HTTP_409_CONFLICT,
                )
        with transaction.atomic():
            state, _ = UserListingState.objects.select_for_update().get_or_create(
                user=user,
                listing=listing,
            )
            setattr(state, field, value)
            state.save(update_fields=(field, "updated_at"))
        return Response(ListingSerializer(listing, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def favorite(self, request: Request, pk: str | None = None) -> Response:
        return self._set_state(request, "is_favorite")

    @action(detail=True, methods=["post"])
    def hide(self, request: Request, pk: str | None = None) -> Response:
        return self._set_state(request, "is_hidden")

    @action(detail=True, methods=["post"])
    def compare(self, request: Request, pk: str | None = None) -> Response:
        return self._set_state(request, "is_compared")
