from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from decimal import Decimal
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from apps.listings.models import Listing

FINGERPRINT_VERSION = 1
IMAGE_HASH_VERSION = 1

_BOILERPLATE_PATTERNS = (
    r"синтетичне demo оголошення яке не описує реальну квартиру",
    r"деталі за телефоном",
    r"телефонуйте",
    r"посередникам не турбувати",
)
_ABBREVIATIONS = {
    "вул": "вулиця",
    "вулиці": "вулиця",
    "просп": "проспект",
    "пр т": "проспект",
    "кв": "квартира",
    "кімн": "кімнатна",
    "кім": "кімнатна",
    "м2": "м²",
}
_TRACKING_KEYS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "yclid",
}
_CONTACT_KEYWORDS = ("phone", "телефон", "email", "telegram", "contact", "контакт", "viber")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?38)?0?\d{9,10}(?!\d)")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[a-zа-яіїєґ]{2,}", re.IGNORECASE)
_HANDLE_RE = re.compile(r"(?<!\w)@[a-z0-9_]{5,32}", re.IGNORECASE)
_BUILDING_RE = re.compile(
    r"(?:^|\s)(\d{1,4}[а-яa-z]?(?:[/-]\d{1,4}[а-яa-z]?)?)(?:\s|$)", re.IGNORECASE
)
_TOKEN_RE = re.compile(r"[\wа-яіїєґ]+", re.IGNORECASE)


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value or "").casefold()
    normalized = normalized.replace("'", " ").replace("’", " ")
    normalized = re.sub(r"[^\wа-яіїєґ²]+", " ", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    for pattern in _BOILERPLATE_PATTERNS:
        normalized = re.sub(pattern, " ", normalized)
    tokens = [_ABBREVIATIONS.get(token, token) for token in normalized.split()]
    return " ".join(tokens)


def canonicalize_url(value: str) -> str:
    candidate = (value or "").strip()
    if not candidate:
        return ""
    try:
        parsed = urlsplit(candidate)
    except ValueError:
        return ""
    scheme = parsed.scheme.casefold()
    host = (parsed.hostname or "").casefold()
    if scheme not in {"http", "https"} or not host:
        return ""
    port = parsed.port
    netloc = host
    if port is not None and not (
        (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    ):
        netloc = f"{host}:{port}"
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    if path != "/":
        path = path.rstrip("/")
    query_items = [
        (key, item)
        for key, item in parse_qsl(parsed.query, keep_blank_values=False)
        if key.casefold() not in _TRACKING_KEYS
    ]
    query = urlencode(sorted(query_items))
    return urlunsplit((scheme, netloc, path, query, ""))


def _iter_contact_values(value: Any, *, path: str = "") -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            child_path = f"{path}.{str(key).casefold()}"
            yield from _iter_contact_values(item, path=child_path)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            yield from _iter_contact_values(item, path=path)
        return
    if isinstance(value, str) and any(keyword in path for keyword in _CONTACT_KEYWORDS):
        yield value


def _normalized_contact_tokens(value: str) -> set[str]:
    tokens: set[str] = set()
    for match in _PHONE_RE.findall(value):
        digits = re.sub(r"\D", "", match)
        if len(digits) == 9:
            digits = f"380{digits}"
        elif len(digits) == 10 and digits.startswith("0"):
            digits = f"38{digits}"
        if len(digits) >= 11:
            tokens.add(f"phone:{digits}")
    for match in _EMAIL_RE.findall(value):
        tokens.add(f"email:{match.casefold()}")
    for match in _HANDLE_RE.findall(value):
        tokens.add(f"handle:{match.casefold().lstrip('@')}")
    return tokens


def contact_hashes(listing: Listing) -> list[str]:
    tokens: set[str] = set()
    for value in _iter_contact_values(listing.attributes):
        tokens.update(_normalized_contact_tokens(value))
    for value in (listing.description, listing.title):
        tokens.update(_normalized_contact_tokens(value))
    return sorted(hashlib.sha256(token.encode("utf-8")).hexdigest() for token in tokens)


def _valid_hex(value: object, length: int) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip().casefold()
    if len(candidate) != length or re.fullmatch(r"[0-9a-f]+", candidate) is None:
        return None
    return candidate


def trusted_image_hashes(listing: Listing) -> list[dict[str, str]]:
    hashes: dict[tuple[str, str], dict[str, str]] = {}
    trusted = listing.attributes.get("trusted_image_hashes", [])
    if isinstance(trusted, list):
        for item in trusted:
            if not isinstance(item, Mapping):
                continue
            exact = _valid_hex(item.get("sha256"), 64)
            perceptual = _valid_hex(item.get("dhash"), 16)
            if exact is None and perceptual is None:
                continue
            payload: dict[str, str] = {}
            if exact is not None:
                payload["exact"] = exact
            if perceptual is not None:
                payload["perceptual"] = perceptual
            hashes[(exact or "", perceptual or "")] = payload

    demo_group = listing.attributes.get("demo_duplicate_group")
    if isinstance(demo_group, str) and demo_group:
        for index in range(2):
            exact = hashlib.sha256(f"{demo_group}:image:{index}".encode()).hexdigest()
            perceptual = hashlib.sha256(f"{demo_group}:visual:{index}".encode()).hexdigest()[:16]
            hashes[(exact, perceptual)] = {"exact": exact, "perceptual": perceptual}

    for image in listing.images:
        if not isinstance(image, str):
            continue
        normalized = canonicalize_url(image)
        if not normalized:
            continue
        exact = hashlib.sha256(f"url:{normalized}".encode()).hexdigest()
        hashes[(exact, "")] = {"exact": exact, "kind": "url"}
    return sorted(hashes.values(), key=lambda item: json.dumps(item, sort_keys=True))


def simhash64(value: str) -> str:
    tokens = _TOKEN_RE.findall(normalize_text(value))
    if not tokens:
        return ""
    vector = [0] * 64
    for token in tokens:
        digest = int.from_bytes(hashlib.blake2b(token.encode(), digest_size=8).digest(), "big")
        for bit in range(64):
            vector[bit] += 1 if digest & (1 << bit) else -1
    result = 0
    for bit, weight in enumerate(vector):
        if weight >= 0:
            result |= 1 << bit
    return f"{result:016x}"


def hamming_distance64(left: str, right: str) -> int:
    if not left or not right:
        return 64
    return (int(left, 16) ^ int(right, 16)).bit_count()


def text_similarity(left: str, right: str, left_simhash: str, right_simhash: str) -> float:
    if not left or not right:
        return 0.0
    sequence_score = SequenceMatcher(None, left, right, autojunk=False).ratio() * 100
    hash_score = max(0.0, 100.0 - hamming_distance64(left_simhash, right_simhash) * 3.125)
    return round(sequence_score * 0.65 + hash_score * 0.35, 2)


def _extract_building_number(listing: Listing) -> str:
    for key in ("building_number", "house_number", "будинок"):
        value = listing.attributes.get(key)
        if value not in (None, ""):
            return normalize_text(str(value)).replace(" ", "")[:32]
    for value in (listing.street, listing.title, listing.description):
        match = _BUILDING_RE.search(normalize_text(value))
        if match:
            return match.group(1).replace(" ", "")[:32]
    return ""


def geo_block_key(listing: Listing) -> str:
    if listing.latitude is None or listing.longitude is None:
        return ""
    latitude = round(float(listing.latitude), 3)
    longitude = round(float(listing.longitude), 3)
    return f"{latitude:.3f}:{longitude:.3f}:{listing.rooms}"


def address_key(listing: Listing) -> str:
    city = normalize_text(listing.city)
    district = normalize_text(listing.district)
    street = normalize_text(listing.street)
    building = _extract_building_number(listing)
    location = geo_block_key(listing)
    parts = [city, district, street, building]
    if street and (building or location):
        return "|".join(parts + ([location] if not building else []))[:320]
    if district and location:
        return "|".join([city, district, location])[:320]
    return ""


def _area_bucket(value: Decimal | None) -> int:
    if value is None:
        return 0
    return int(round(float(value) / 5.0) * 5)


def attribute_key(listing: Listing) -> str:
    values = (
        normalize_text(listing.deal_type),
        normalize_text(listing.property_type),
        str(listing.rooms),
        str(_area_bucket(listing.total_area)),
        str(listing.floor or 0),
        str(listing.floors_total or 0),
        normalize_text(listing.building_type),
        normalize_text(listing.renovation_level),
        normalize_text(listing.heating_type),
    )
    return "|".join(values)[:320]


def price_bucket(price_uah: int) -> int:
    return max(0, int(price_uah) // 1000)


def haversine_metres(left: Listing, right: Listing) -> float | None:
    left_latitude = left.latitude
    left_longitude = left.longitude
    right_latitude = right.latitude
    right_longitude = right.longitude
    if None in (left_latitude, left_longitude, right_latitude, right_longitude):
        return None
    assert left_latitude is not None
    assert left_longitude is not None
    assert right_latitude is not None
    assert right_longitude is not None
    left_lat = math.radians(float(left_latitude))
    right_lat = math.radians(float(right_latitude))
    delta_lat = right_lat - left_lat
    delta_lon = math.radians(float(right_longitude) - float(left_longitude))
    value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(left_lat) * math.cos(right_lat) * math.sin(delta_lon / 2) ** 2
    )
    return 6_371_000 * 2 * math.atan2(math.sqrt(value), math.sqrt(max(0.0, 1 - value)))
