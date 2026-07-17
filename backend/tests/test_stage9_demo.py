from asgiref.sync import async_to_sync

from apps.listings.contracts import SourceSearchRequest
from apps.listings.demo_source import DemoListingSourceAdapter


def test_demo_revisions_create_deterministic_price_history_inputs():
    adapter = DemoListingSourceAdapter()
    revision_one = async_to_sync(adapter.search)(
        SourceSearchRequest(limit=40, seed=20260716, revision=1)
    )
    revision_two = async_to_sync(adapter.search)(
        SourceSearchRequest(limit=40, seed=20260716, revision=2)
    )
    repeated = async_to_sync(adapter.search)(
        SourceSearchRequest(limit=40, seed=20260716, revision=2)
    )

    assert revision_two == repeated
    assert revision_two[0]["price"] < revision_one[0]["price"]
    assert revision_two[1]["price"] > revision_one[1]["price"]
    assert revision_two[0]["attributes"]["demo_revision"] == 2


def test_demo_contains_safe_market_and_risk_scenarios():
    listings = async_to_sync(DemoListingSourceAdapter().search)(
        SourceSearchRequest(limit=40, seed=20260716, revision=2)
    )

    assert "передоплата" in listings[0]["description"].casefold()
    assert len(listings[1]["description"]) < 80
    assert listings[2]["price"] < listings[3]["price"]
    assert listings[5]["attributes"]["demo_image_hashes"] == [
        "synthetic-cross-city-image-001"
    ]
    assert listings[6]["attributes"]["demo_image_hashes"] == [
        "synthetic-cross-city-image-001"
    ]
    assert listings[5]["city"] != listings[6]["city"]
    assert listings[7]["attributes"]["hidden_commission"] is True
    assert "не описує реальну квартиру" in listings[3]["description"].casefold()
