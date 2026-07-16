from __future__ import annotations

from decimal import Decimal
from typing import Any

from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.duplicates.candidates import canonical_pair, detect_listing_duplicates, split_candidate
from apps.duplicates.clustering import build_guarded_components, rebuild_clusters
from apps.duplicates.fingerprints import build_listing_fingerprint, get_fresh_fingerprint
from apps.duplicates.models import (
    CandidateDecision,
    DuplicateCandidate,
    ListingCluster,
    ListingClusterMember,
    UserClusterState,
)
from apps.duplicates.normalization import (
    contact_hashes,
    hamming_distance64,
    normalize_text,
    simhash64,
)
from apps.duplicates.scoring import evaluate_duplicate
from apps.listings.contracts import SourceSearchRequest
from apps.listings.demo_source import DemoListingSourceAdapter
from apps.listings.models import Listing, ListingSource, SourceAccessMode, UserListingState
from apps.listings.services import ingest_source


def _source(code: str = "stage7") -> ListingSource:
    return ListingSource.objects.create(
        code=code,
        display_name=code,
        enabled=True,
        access_mode=SourceAccessMode.DEMO,
        legal_status="approved_demo",
        health_status="healthy",
    )


def _listing(source: ListingSource, external_id: str, **overrides: Any) -> Listing:
    values: dict[str, Any] = {
        "source_url": f"https://example.invalid/{external_id}",
        "canonical_url": f"https://example.invalid/{external_id}",
        "title": "2-кімнатна квартира на вул. Науковій 10",
        "description": "Світла квартира з ремонтом. Телефон +380671234567",
        "deal_type": "rent",
        "property_type": "apartment",
        "country": "UA",
        "region": "Львівська",
        "city": "Львів",
        "district": "Франківський",
        "street": "Наукова 10",
        "latitude": Decimal("49.812300"),
        "longitude": Decimal("24.012300"),
        "location_accuracy": "building",
        "price": 18000,
        "price_uah": 18000,
        "currency": "UAH",
        "rooms": 2,
        "total_area": Decimal("52.00"),
        "floor": 4,
        "floors_total": 9,
        "building_type": "brick",
        "renovation_level": "modern",
        "heating_type": "individual",
        "pets_allowed": True,
        "children_allowed": True,
        "commission_percent": Decimal("0"),
        "is_owner": True,
        "images": [],
        "attributes": {"building_number": "10", "demo": True},
        "published_at": timezone.now(),
        "is_active": True,
        "normalization_version": 3,
    }
    values.update(overrides)
    return Listing.objects.create(source=source, external_id=external_id, **values)


def _run_demo_pipeline(count: int = 3) -> list[Listing]:
    async_to_sync(ingest_source)(
        DemoListingSourceAdapter(),
        SourceSearchRequest(limit=count, seed=20260716),
    )
    for listing in Listing.objects.select_related("source"):
        build_listing_fingerprint(listing, force=True)
    detect_listing_duplicates()
    rebuild_clusters()
    return list(Listing.objects.order_by("external_id"))


def test_normalization_simhash_and_contact_hashing_are_deterministic(db):
    source = _source()
    listing = _listing(source, "one")

    assert normalize_text("  ВУЛ. Наукова, 10! ") == "вулиця наукова 10"
    assert simhash64("Квартира біля центру") == simhash64("Квартира біля центру")
    assert hamming_distance64(simhash64("одна квартира"), simhash64("одна квартира")) == 0
    hashes = contact_hashes(listing)
    assert hashes
    assert all("380671234567" not in value for value in hashes)


def test_demo_source_contains_deterministic_three_copy_groups():
    adapter = DemoListingSourceAdapter()
    first = async_to_sync(adapter.search)(SourceSearchRequest(limit=3, seed=20260716))
    second = async_to_sync(adapter.search)(SourceSearchRequest(limit=3, seed=20260716))

    assert first == second
    assert {item["attributes"]["demo_duplicate_group"] for item in first} == {
        "demo-duplicate-000"
    }
    assert len({(item["latitude"], item["longitude"], item["rooms"]) for item in first}) == 1
    assert len({item["price"] for item in first}) == 3


def test_fingerprint_and_score_use_exact_demo_image_evidence(db):
    source = _source()
    shared = {"building_number": "10", "demo_duplicate_group": "safe-group", "demo": True}
    left = _listing(source, "left", attributes=shared)
    right = _listing(
        source,
        "right",
        title="Оренда двокімнатної квартири · Франківський",
        description="Інша публікація тієї самої синтетичної квартири.",
        price=18300,
        price_uah=18300,
        attributes=shared,
    )

    left_fp = get_fresh_fingerprint(left)
    right_fp = get_fresh_fingerprint(right)
    evaluation = evaluate_duplicate(left, right, left_fp, right_fp)

    assert len(left_fp.image_hashes) == 2
    assert evaluation.image_score == 100
    assert evaluation.exact_rule is True
    assert evaluation.decision == CandidateDecision.AUTO_MERGE


def test_hard_city_conflict_rejects_even_with_shared_images(db):
    source = _source()
    shared = {"demo_duplicate_group": "same-images", "demo": True}
    left = _listing(source, "left", attributes=shared)
    right = _listing(source, "right", city="Київ", attributes=shared)

    evaluation = evaluate_duplicate(
        left,
        right,
        get_fresh_fingerprint(left),
        get_fresh_fingerprint(right),
    )

    assert evaluation.final_score == 0
    assert "different_city" in evaluation.hard_conflicts
    assert evaluation.decision == CandidateDecision.REJECTED


def test_demo_detection_and_cluster_rebuild_are_idempotent(db):
    listings = _run_demo_pipeline()

    assert len(listings) == 3
    cluster = ListingCluster.objects.get(status="active")
    assert cluster.member_count == 3
    assert ListingClusterMember.objects.filter(cluster=cluster).count() == 3
    first_id = cluster.id

    detect_listing_duplicates()
    rebuild_clusters()

    assert ListingCluster.objects.get(status="active").id == first_id
    assert ListingClusterMember.objects.filter(cluster_id=first_id).count() == 3


def test_guarded_components_reject_transitive_poisoning(db):
    source = _source()
    primary = _listing(source, "a", description="Повний якісний опис", images=["https://img.invalid/a"])
    bridge = _listing(source, "b", price=18100, price_uah=18100)
    distant = _listing(
        source,
        "c",
        street="Інша 88",
        latitude=Decimal("49.850000"),
        longitude=Decimal("24.100000"),
        price=18200,
        price_uah=18200,
    )
    left_a, right_b = canonical_pair(primary, bridge)
    left_b, right_c = canonical_pair(bridge, distant)
    candidates = [
        DuplicateCandidate.objects.create(
            left_listing=left_a,
            right_listing=right_b,
            final_score=96,
            decision=CandidateDecision.CONFIRMED,
        ),
        DuplicateCandidate.objects.create(
            left_listing=left_b,
            right_listing=right_c,
            final_score=96,
            decision=CandidateDecision.CONFIRMED,
        ),
    ]

    components = build_guarded_components([primary, bridge, distant], candidates)

    assert components == [{str(primary.id), str(bridge.id)}]


def test_manual_split_blocks_remerge_through_a_third_listing(db):
    _run_demo_pipeline()
    candidate = DuplicateCandidate.objects.order_by("left_listing_id", "right_listing_id").first()
    assert candidate is not None
    split_candidate(candidate, actor=None, note="different apartment")

    rebuild_clusters()

    assert not ListingClusterMember.objects.filter(
        cluster__status="active",
        listing_id=candidate.left_listing_id,
    ).filter(cluster__members__listing_id=candidate.right_listing_id).exists()


def test_feed_cluster_detail_state_and_map_are_cluster_aware(db):
    _run_demo_pipeline()
    user = get_user_model().objects.create_user(username="stage7", password="secret")
    client = APIClient()
    client.force_authenticate(user)

    feed = client.get("/api/v1/listings/")
    assert feed.status_code == 200
    assert feed.data["count"] == 1
    item = feed.data["results"][0]
    assert item["cluster_id"]
    assert item["member_count"] == 3
    assert item["is_cluster_primary"] is True

    detail = client.get(f"/api/v1/listing-clusters/{item['cluster_id']}/")
    assert detail.status_code == 200
    assert len(detail.data["members"]) == 3
    assert detail.data["members"][0]["role"] == "primary"

    state = client.patch(
        f"/api/v1/listing-clusters/{item['cluster_id']}/state/",
        {"is_favorite": True, "is_compared": True, "note": "Перевірити ввечері"},
        format="json",
    )
    assert state.status_code == 200
    assert state.data["user_state"]["is_favorite"] is True
    assert UserClusterState.objects.get(user=user).is_compared is True
    assert UserListingState.objects.filter(user=user, is_favorite=True).count() == 1

    favorites = client.get("/api/v1/listings/", {"favorites": "true"})
    assert favorites.data["count"] == 1
    map_response = client.get("/api/v1/map/listings/")
    assert map_response.status_code == 200
    assert len(map_response.data["features"]) == 1
    assert map_response.data["features"][0]["properties"]["member_count"] == 3


def test_cluster_comparison_uses_one_slot_and_enforces_global_limit(db):
    _run_demo_pipeline()
    source = ListingSource.objects.get(pk="demo")
    user = get_user_model().objects.create_user(username="limit", password="secret")
    for index in range(4):
        listing = _listing(source, f"standalone-{index}", city="Рівне", district=f"D{index}")
        UserListingState.objects.create(user=user, listing=listing, is_compared=True)
    cluster = ListingCluster.objects.get(status="active")
    client = APIClient()
    client.force_authenticate(user)

    response = client.patch(
        f"/api/v1/listing-clusters/{cluster.id}/state/",
        {"is_compared": True},
        format="json",
    )

    assert response.status_code == 409
    assert response.data["error"]["code"] == "comparison_limit"


def test_candidate_review_endpoints_are_staff_only(db):
    _run_demo_pipeline()
    candidate = DuplicateCandidate.objects.first()
    assert candidate is not None
    user = get_user_model().objects.create_user(username="regular", password="secret")
    staff = get_user_model().objects.create_user(
        username="staff",
        password="secret",
        is_staff=True,
    )
    client = APIClient()
    client.force_authenticate(user)
    denied = client.post(f"/api/v1/duplicate-candidates/{candidate.id}/split/", {}, format="json")
    client.force_authenticate(staff)
    allowed = client.post(
        f"/api/v1/duplicate-candidates/{candidate.id}/split/",
        {"note": "manual review"},
        format="json",
    )

    assert denied.status_code == 403
    assert allowed.status_code == 200
    assert allowed.data["decision"] == CandidateDecision.SPLIT
