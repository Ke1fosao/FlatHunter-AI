from __future__ import annotations

from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from asgiref.sync import async_to_sync
from django.conf import settings
from django.db.models import Prefetch, QuerySet
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.geodata.contracts import (
    GeocodingDisabled,
    GeocodingError,
    GeocodingNotFound,
    GeocodingRequest,
)
from apps.geodata.serializers import (
    GeocodingPreviewSerializer,
    ImportantPlaceSerializer,
    MapContextQuerySerializer,
    MapListingQuerySerializer,
)
from apps.geodata.service import geocode_address
from apps.geodata.spatial import (
    BoundingBox,
    annotate_distance_to_place,
    filter_listings_in_bbox,
    serialize_listing_feature,
)
from apps.listings.models import Listing, UserListingState
from apps.matching.engine import evaluate_match
from apps.searches.models import ImportantPlace, SearchProfile


def _owned_profile(request: Request, profile_id: UUID) -> SearchProfile:
    user = cast(User, request.user)
    return get_object_or_404(SearchProfile, id=profile_id, user=user)


def _geocoding_error_response(error: GeocodingError) -> Response:
    response_status: int = status.HTTP_422_UNPROCESSABLE_ENTITY
    if isinstance(error, GeocodingDisabled) or not isinstance(error, GeocodingNotFound):
        response_status = status.HTTP_503_SERVICE_UNAVAILABLE
    return Response(
        {"error": {"code": error.code, "message": str(error)}},
        status=response_status,
    )


class MapListingView(APIView):
    def get(self, request: Request) -> Response:
        query = MapListingQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        params = query.validated_data
        user = cast(User, request.user)
        profile = None
        if params.get("profile_id") is not None:
            profile = _owned_profile(request, params["profile_id"])

        state_queryset = UserListingState.objects.filter(user=user)
        queryset: QuerySet[Listing] = (
            Listing.objects.filter(
                is_active=True,
                location__isnull=False,
                source__enabled=True,
                source__legal_status__in=("approved_demo", "approved"),
            )
            .select_related("source")
            .prefetch_related(
                Prefetch("user_states", queryset=state_queryset, to_attr="current_user_states")
            )
            .order_by("-published_at")
        )
        hidden_ids = UserListingState.objects.filter(user=user, is_hidden=True).values("listing_id")
        queryset = queryset.exclude(id__in=hidden_ids)
        favorites = params.get("favorites")
        if favorites is not None:
            favorite_ids = UserListingState.objects.filter(user=user, is_favorite=True).values(
                "listing_id"
            )
            if favorites:
                queryset = queryset.filter(id__in=favorite_ids)
            else:
                queryset = queryset.exclude(id__in=favorite_ids)
        bounding_box = params.get("bbox")
        if isinstance(bounding_box, BoundingBox):
            queryset = filter_listings_in_bbox(queryset, bounding_box)

        features: list[dict[str, Any]] = []
        inspected = 0
        for listing in queryset[:1000]:
            inspected += 1
            match_data = None
            if profile is not None:
                evaluation = evaluate_match(profile, listing)
                if evaluation.score < params["min_score"]:
                    continue
                match_data = evaluation.to_dict()
            features.append(serialize_listing_feature(listing, match_data))
            if len(features) >= params["limit"]:
                break

        return Response(
            {
                "type": "FeatureCollection",
                "features": features,
                "meta": {
                    "returned": len(features),
                    "inspected": inspected,
                    "profile_id": str(profile.id) if profile is not None else None,
                    "tiles_url": settings.MAP_TILES_URL,
                    "attribution": settings.MAP_ATTRIBUTION,
                },
            }
        )


class ImportantPlaceListCreateView(APIView):
    def get(self, request: Request, profile_id: UUID) -> Response:
        profile = _owned_profile(request, profile_id)
        places = profile.important_places.all()
        return Response(ImportantPlaceSerializer(places, many=True).data)

    def post(self, request: Request, profile_id: UUID) -> Response:
        profile = _owned_profile(request, profile_id)
        serializer = ImportantPlaceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = dict(serializer.validated_data)
        provider = "manual"
        confidence = Decimal("1.000")
        if values.get("latitude") is None:
            try:
                result = async_to_sync(geocode_address)(
                    GeocodingRequest(
                        query=str(values["address"]),
                        city=profile.city,
                    )
                )
            except GeocodingError as error:
                return _geocoding_error_response(error)
            values["latitude"] = Decimal(str(result.latitude))
            values["longitude"] = Decimal(str(result.longitude))
            values["address"] = result.display_name
            provider = result.provider
            confidence = Decimal(str(result.confidence))
        place = ImportantPlace.objects.create(
            search_profile=profile,
            geocoding_provider=provider,
            geocoding_confidence=confidence,
            **values,
        )
        return Response(
            ImportantPlaceSerializer(place).data,
            status=status.HTTP_201_CREATED,
        )


class ImportantPlaceDetailView(APIView):
    def delete(self, request: Request, profile_id: UUID, place_id: UUID) -> Response:
        profile = _owned_profile(request, profile_id)
        place = get_object_or_404(ImportantPlace, id=place_id, search_profile=profile)
        place.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class GeocodingPreviewView(APIView):
    def post(self, request: Request, profile_id: UUID) -> Response:
        profile = _owned_profile(request, profile_id)
        serializer = GeocodingPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = async_to_sync(geocode_address)(
                GeocodingRequest(
                    query=serializer.validated_data["address"],
                    city=serializer.validated_data.get("city") or profile.city,
                )
            )
        except GeocodingError as error:
            return _geocoding_error_response(error)
        return Response(
            {
                "latitude": result.latitude,
                "longitude": result.longitude,
                "display_name": result.display_name,
                "provider": result.provider,
                "confidence": result.confidence,
                "country_code": result.country_code,
            }
        )


class MapContextView(APIView):
    def get(self, request: Request, profile_id: UUID) -> Response:
        profile = _owned_profile(request, profile_id)
        query = MapContextQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        listing_ids: list[UUID] = query.validated_data.get("listing_ids", [])
        places = list(profile.important_places.filter(location__isnull=False))
        listings = Listing.objects.filter(
            id__in=listing_ids,
            is_active=True,
            location__isnull=False,
            source__enabled=True,
            source__legal_status__in=("approved_demo", "approved"),
        )
        distances: dict[str, list[dict[str, Any]]] = {str(item): [] for item in listing_ids}
        for place in places:
            for listing in annotate_distance_to_place(listings, place):
                distance = getattr(listing, "distance_to_place", None)
                distance_km = round(distance.km, 2) if distance is not None else None
                distances[str(listing.id)].append(
                    {
                        "place_id": str(place.id),
                        "name": place.name,
                        "distance_km": distance_km,
                        "max_distance_km": (
                            float(place.max_distance_km)
                            if place.max_distance_km is not None
                            else None
                        ),
                    }
                )
        return Response(
            {
                "profile": {"id": str(profile.id), "name": profile.name, "city": profile.city},
                "places": ImportantPlaceSerializer(places, many=True).data,
                "distances": distances,
            }
        )
