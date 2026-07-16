from django.contrib.gis.db.models.fields import PointField
from django.contrib.gis.geos import Point
from django.db import migrations, models


def backfill_place_locations(apps, schema_editor):
    ImportantPlace = apps.get_model("searches", "ImportantPlace")
    for place in ImportantPlace.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False,
        location__isnull=True,
    ).iterator(chunk_size=500):
        place.location = Point(float(place.longitude), float(place.latitude), srid=4326)
        place.save(update_fields=("location",))


class Migration(migrations.Migration):
    dependencies = [("searches", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="importantplace",
            name="location",
            field=PointField(blank=True, geography=True, null=True, srid=4326),
        ),
        migrations.AddField(
            model_name="importantplace",
            name="geocoding_provider",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name="importantplace",
            name="geocoding_confidence",
            field=models.DecimalField(blank=True, decimal_places=3, max_digits=4, null=True),
        ),
        migrations.AlterModelOptions(
            name="importantplace",
            options={"ordering": ("-importance", "name")},
        ),
        migrations.AddIndex(
            model_name="importantplace",
            index=models.Index(
                fields=["search_profile", "importance"],
                name="place_profile_importance_idx",
            ),
        ),
        migrations.RunPython(backfill_place_locations, migrations.RunPython.noop),
    ]
