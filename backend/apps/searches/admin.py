from django.contrib import admin

from apps.searches.models import ImportantPlace, NotificationPreference, SearchProfile


class ImportantPlaceInline(admin.TabularInline):
    model = ImportantPlace
    extra = 0


class NotificationPreferenceInline(admin.StackedInline):
    model = NotificationPreference
    extra = 0
    max_num = 1


@admin.register(SearchProfile)
class SearchProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "city", "deal_type", "price_max", "is_active", "updated_at")
    list_filter = ("deal_type", "is_active", "currency", "city")
    search_fields = ("name", "city", "user__username", "user__telegram_profile__telegram_id")
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = (ImportantPlaceInline, NotificationPreferenceInline)
