from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.contrib.gis.geos import Point

COORDINATE_PRECISION = Decimal("0.000001")


class CoordinateValidationError(ValueError):
    pass


def _decimal(value: Decimal | float | str | int) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise CoordinateValidationError("Coordinate must be a number") from error


def normalize_coordinates(
    latitude: Decimal | float | str | int,
    longitude: Decimal | float | str | int,
) -> tuple[Decimal, Decimal]:
    lat = _decimal(latitude).quantize(COORDINATE_PRECISION)
    lon = _decimal(longitude).quantize(COORDINATE_PRECISION)
    if not Decimal("-90") <= lat <= Decimal("90"):
        raise CoordinateValidationError("Latitude must be between -90 and 90")
    if not Decimal("-180") <= lon <= Decimal("180"):
        raise CoordinateValidationError("Longitude must be between -180 and 180")
    return lat, lon


def point_from_coordinates(
    latitude: Decimal | float | str | int | None,
    longitude: Decimal | float | str | int | None,
) -> Point | None:
    if latitude is None or longitude is None:
        return None
    lat, lon = normalize_coordinates(latitude, longitude)
    return Point(float(lon), float(lat), srid=4326)


def coordinates_from_point(point: Point | None) -> tuple[Decimal, Decimal] | None:
    if point is None:
        return None
    resolved = point
    if point.srid not in (None, 4326):
        transformed = point.transform(4326, clone=True)
        if not isinstance(transformed, Point):
            raise CoordinateValidationError("Geometry must be a point")
        resolved = transformed
    return normalize_coordinates(resolved.y, resolved.x)
