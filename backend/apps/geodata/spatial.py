from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Polygon
from django.db.models import QuerySet

from apps.accounts.models import User
from apps.duplicates.presentation import cluster_metadata, projected_user_state
from apps.listings.models import Listing
from apps.searches.models import ImportantPlace


class BoundingBoxValidationError(ValueError):
    pass


@dataclass(frozen=True)
class BoundingBox:
    west: float
    south: float
    east: float
    north: float

    @classmethod
    def parse(cls, value: str) -> BoundingBox:
        try:
            west, south, east, north = (float(part.strip()) for part in value.split(","))
        except (TypeError, ValueError) as error:
            raise BoundingBoxValidationError("bbox must contain west,south,east,north") from error
        if not (-180 <= west <= 180 and -180 <= east <= 180):
            raise BoundingBoxValidationError("bbox longitude is outside valid range")
        if not (-90 <= south <= 90 and -90 <= north <= 90):
            raise BoundingBoxValidationError("bbox latitude is outside valid range")
        if west >= east or south >= north:
            raise BoundingBoxValidationError("bbox west/south must be lower than east/north")
        return cls(west=west, south=south, east=east, north=north)

    def polygon(self) -> Polygon:
        polygon = Polygon.from_bbox((self.west, self.south, self.east, self.north))
        polygon.srid = 4326
        return polygon


def filter_listings_in_bbox(
    queryset: QuerySet[Listing],
    bounding_box: BoundingBox,
) -> QuerySet[Listing]:
    return queryset.filter(location__intersects=bounding_box.polygon())


def annotate_distance_to_place(
    queryset: QuerySet[Listing],
    place: ImportantPlace,
) -> QuerySet[Listing]:
    if place.location is None:
        return queryset.none()
    return queryset.filter(location__isnull=False).annotate(
        distance_to_place=Distance("location", place.location)
    )


def serialize_listing_feature(
    listing: Listing,
    match: dict[str, Any] | None = None,
    *,
    user: User | None = None,
) -> dict[str, Any]:
    if listing.location is None:
        raise ValueError("Listing has no location")
    if user is not None:
        user_state = projected_user_state(listing, user)
    else:
        states = getattr(listing, "current_user_states", [])
        state = states[0] if states else None
        user_state = {
            "is_favorite": bool(state and state.is_favorite),
            "is_hidden": bool(state and state.is_hidden),
            "is_compared": bool(state and state.is_compared),
        }
    metadata = cluster_metadata(listing)
    return {
        "type": "Feature",
        "id": str(listing.id),
        "geometry": {
            "type": "Point",
            "coordinates": [listing.location.x, listing.location.y],
        },
        "properties": {
            "id": str(listing.id),
            "title": listing.title,
            "price_uah": listing.price_uah,
            "price_min_uah": metadata["price_min_uah"],
            "price_max_uah": metadata["price_max_uah"],
            "rooms": listing.rooms,
            "total_area": str(listing.total_area) if listing.total_area is not None else None,
            "city": listing.city,
            "district": listing.district,
            "street": listing.street,
            "is_demo": bool(listing.attributes.get("demo")),
            "published_at": listing.published_at.isoformat(),
            "user_state": {
                "is_favorite": bool(user_state["is_favorite"]),
                "is_hidden": bool(user_state["is_hidden"]),
                "is_compared": bool(user_state["is_compared"]),
            },
            "cluster_id": metadata["cluster_id"],
            "source_count": metadata["source_count"],
            "member_count": metadata["member_count"],
            "is_cluster_primary": metadata["is_cluster_primary"],
            "match": match,
        },
    }
