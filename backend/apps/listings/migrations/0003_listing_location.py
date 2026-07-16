from django.contrib.gis.db.models.fields import PointField
from django.contrib.gis.geos import Point
from django.db import migrations, models


def backfill_listing_locations(apps, schema_editor):
    Listing = apps.get_model("listings", "Listing")
    for listing in Listing.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False,
        location__isnull=True,
    ).iterator(chunk_size=500):
        listing.location = Point(float(listing.longitude), float(listing.latitude), srid=4326)
        listing.save(update_fields=("location",))


class Migration(migrations.Migration):
    dependencies = [("listings", "0002_userlistingstate")]

    operations = [
        migrations.AddField(
            model_name="listing",
            name="location",
            field=PointField(blank=True, geography=True, null=True, srid=4326),
        ),
        migrations.AddIndex(
            model_name="listing",
            index=models.Index(
                fields=["city", "location_accuracy"],
                name="listing_city_accuracy_idx",
            ),
        ),
        migrations.RunPython(backfill_listing_locations, migrations.RunPython.noop),
    ]
