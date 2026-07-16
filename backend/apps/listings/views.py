from __future__ import annotations

from typing import cast

from django.db import transaction
from django.db.models import Count, Prefetch, Q, QuerySet
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
        serializer = ListingFilterSerializer(data=self.request.query_params)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data
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
        if params.get("city"):
            queryset = queryset.filter(city__iexact=params["city"])
        if params.get("district"):
            queryset = queryset.filter(district__iexact=params["district"])
        if params.get("rooms") is not None:
            queryset = queryset.filter(rooms=params["rooms"])
        if params.get("price_min") is not None:
            queryset = queryset.filter(price_uah__gte=params["price_min"])
        if params.get("price_max") is not None:
            queryset = queryset.filter(price_uah__lte=params["price_max"])
        if params.get("favorites") is not None:
            queryset = queryset.filter(
                user_states__user=user,
                user_states__is_favorite=params["favorites"],
            )
        if params.get("compared") is not None:
            queryset = queryset.filter(
                user_states__user=user,
                user_states__is_compared=params["compared"],
            )
        if not params.get("include_hidden", False):
            queryset = queryset.exclude(user_states__user=user, user_states__is_hidden=True)
        return queryset.distinct()

    @action(detail=False, methods=["get"])
    def dashboard(self, request: Request) -> Response:
        user = cast(User, request.user)
        counts = UserListingState.objects.filter(user=user).aggregate(
            favorites=Count("id", filter=Q(is_favorite=True)),
            hidden=Count("id", filter=Q(is_hidden=True)),
            compared=Count("id", filter=Q(is_compared=True)),
        )
        available = Listing.objects.filter(
            is_active=True,
            source__enabled=True,
            source__legal_status__in=("approved_demo", "approved"),
        ).count()
        recent = list(self.get_queryset()[:4])
        return Response(
            {
                "stats": {
                    "active_profiles": SearchProfile.objects.filter(
                        user=user, is_active=True
                    ).count(),
                    "available_listings": available,
                    **counts,
                },
                "recent": self.get_serializer(recent, many=True).data,
            }
        )

    def _set_state(self, request: Request, field: str) -> Response:
        serializer = ListingStateMutationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        value = serializer.validated_data["value"]
        user = cast(User, request.user)
        listing = self.get_object()
        if field == "is_compared" and value:
            count = UserListingState.objects.filter(user=user, is_compared=True).exclude(
                listing=listing
            ).count()
            if count >= 4:
                return Response(
                    {
                        "error": {
                            "code": "comparison_limit",
                            "message": "Можна порівнювати до 4 квартир.",
                        }
                    },
                    status=status.HTTP_409_CONFLICT,
                )
        with transaction.atomic():
            state, _ = UserListingState.objects.select_for_update().get_or_create(
                user=user,
                listing=listing,
            )
            setattr(state, field, value)
            state.save(update_fields=(field, "updated_at"))
        listing.current_user_states = [state]
        return Response(self.get_serializer(listing).data)

    @action(detail=True, methods=["post"])
    def favorite(self, request: Request, pk: str | None = None) -> Response:
        return self._set_state(request, "is_favorite")

    @action(detail=True, methods=["post"])
    def hide(self, request: Request, pk: str | None = None) -> Response:
        return self._set_state(request, "is_hidden")

    @action(detail=True, methods=["post"])
    def compare(self, request: Request, pk: str | None = None) -> Response:
        return self._set_state(request, "is_compared")
