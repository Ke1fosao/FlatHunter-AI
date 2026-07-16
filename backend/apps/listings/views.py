from __future__ import annotations

from typing import Any, cast

from django.db import transaction
from django.db.models import QuerySet
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.accounts.models import User
from apps.duplicates.models import UserClusterState
from apps.duplicates.presentation import (
    cluster_aware_listing_queryset,
    cluster_for_listing,
    collapse_clustered_queryset,
    filter_listing_state,
    presentation_queryset,
)
from apps.duplicates.services import ComparisonLimitError, update_cluster_state
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
        queryset = Listing.objects.filter(
            is_active=True,
            source__enabled=True,
            source__legal_status__in=("approved_demo", "approved"),
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

        detail_actions = {"retrieve", "favorite", "hide", "compare"}
        include_duplicates = bool(params.get("include_duplicates", False)) and user.is_staff
        include_hidden = bool(params.get("include_hidden", False)) or self.action in detail_actions
        queryset = cluster_aware_listing_queryset(
            queryset,
            user=user,
            include_duplicates=include_duplicates or self.action in detail_actions,
            include_hidden=include_hidden,
        )
        if params.get("favorites") is not None:
            queryset = filter_listing_state(
                queryset,
                user=user,
                field="is_favorite",
                value=bool(params["favorites"]),
            )
        if params.get("compared") is not None:
            queryset = filter_listing_state(
                queryset,
                user=user,
                field="is_compared",
                value=bool(params["compared"]),
            )
        return queryset.distinct()

    @action(detail=False, methods=["get"])
    def dashboard(self, request: Request) -> Response:
        user = cast(User, request.user)
        standalone_states = UserListingState.objects.filter(
            user=user,
            listing__cluster_membership__isnull=True,
        )
        cluster_states = UserClusterState.objects.filter(user=user, cluster__status="active")
        base = Listing.objects.filter(
            is_active=True,
            source__enabled=True,
            source__legal_status__in=("approved_demo", "approved"),
        )
        available = collapse_clustered_queryset(base).count()
        recent_queryset = cluster_aware_listing_queryset(base, user=user).order_by("-published_at")
        recent = list(recent_queryset[:4])
        return Response(
            {
                "stats": {
                    "active_profiles": SearchProfile.objects.filter(
                        user=user,
                        is_active=True,
                    ).count(),
                    "available_listings": available,
                    "favorites": standalone_states.filter(is_favorite=True).count()
                    + cluster_states.filter(is_favorite=True).count(),
                    "hidden": standalone_states.filter(is_hidden=True).count()
                    + cluster_states.filter(is_hidden=True).count(),
                    "compared": standalone_states.filter(is_compared=True).count()
                    + cluster_states.filter(is_compared=True).count(),
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
        cluster = cluster_for_listing(listing)
        if cluster is not None:
            try:
                state = update_cluster_state(
                    cluster=cluster,
                    user=user,
                    values={field: value},
                )
            except ComparisonLimitError as error:
                return Response(
                    {"error": {"code": "comparison_limit", "message": str(error)}},
                    status=status.HTTP_409_CONFLICT,
                )
            cast(Any, cluster).current_user_cluster_states = [state]
            primary_id = cluster.primary_listing_id or listing.id
            updated = presentation_queryset(
                Listing.objects.filter(pk=primary_id),
                user,
            ).get()
            return Response(self.get_serializer(updated).data)

        with transaction.atomic():
            standalone_compared = (
                UserListingState.objects.select_for_update()
                .filter(
                    user=user,
                    is_compared=True,
                    listing__cluster_membership__isnull=True,
                )
                .exclude(listing=listing)
                .count()
            )
            cluster_compared = (
                UserClusterState.objects.select_for_update()
                .filter(user=user, is_compared=True, cluster__status="active")
                .count()
            )
            if field == "is_compared" and value and standalone_compared + cluster_compared >= 4:
                return Response(
                    {
                        "error": {
                            "code": "comparison_limit",
                            "message": "Можна порівнювати до 4 квартир.",
                        }
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            listing_state, _ = UserListingState.objects.get_or_create(user=user, listing=listing)
            setattr(listing_state, field, value)
            listing_state.save(update_fields=(field, "updated_at"))
        listing.current_user_states = [listing_state]
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
