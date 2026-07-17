from django.db.models import QuerySet

from apps.listings.models import Listing


def approved_listing_queryset() -> QuerySet[Listing]:
    return Listing.objects.filter(
        is_active=True,
        source__enabled=True,
        source__legal_status__in=("approved_demo", "approved"),
    )
