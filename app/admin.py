from django.contrib import admin
from adminsortable2.admin import SortableAdminBase, SortableAdminMixin, SortableInlineAdminMixin, SortableTabularInline
from django.db.models import Case, F, IntegerField, Value, When
from django.db.models.functions import Coalesce
from django.utils.html import format_html
from django.urls import reverse
from urllib.parse import urlencode

from .forms import ContentSectionAdminForm, MapAreaInfoAdminForm
from .models import Category, ContentSection, Geopark, MapAreaInfo, MapComparison, Media, SubCategory


class MediaInline(SortableInlineAdminMixin, admin.TabularInline):
    model = Media
    extra = 0
    fields = ("preview", "media_type", "file", "caption", "caption_en", "is_zoomable")
    readonly_fields = ("preview",)
    ordering = ("order", "id")
    sortable_field_name = "order"
    classes = ("baton-tab-inline-media",)

    def preview(self, obj):
        if not obj.pk:
            return "-"
        url = None
        if obj.thumbnail:
            url = obj.thumbnail.url
        elif obj.file:
            url = obj.file.url
        if not url:
            return "-"
        return format_html(
            '<img src="{}" alt="preview" style="max-width: 120px; max-height: 80px; object-fit: cover; border: 1px solid rgba(255,255,255,.15);" />',
            url,
        )

    preview.short_description = "Preview"


class MapComparisonInline(SortableInlineAdminMixin, admin.TabularInline):
    model = MapComparison
    extra = 0
    fields = ("title", "image_before", "image_after", "caption_before", "caption_after")
    ordering = ("order", "id")
    sortable_field_name = "order"
    classes = ("baton-tab-inline-comparisons",)


class MapAreaInfoInline(SortableTabularInline):
    model = MapAreaInfo
    form = MapAreaInfoAdminForm
    extra = 0
    fields = ("title", "location", "area_ha", "fill_color", "area_index", "legend_order")
    ordering = ("legend_order", "id")
    sortable_field_name = "legend_order"
    classes = ("baton-tab-inline-map-areas",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("title", "title_en", "is_active")
    list_filter = ("is_active",)
    search_fields = ("title", "title_en")
    ordering = ("order", "title")
    exclude = ("slug", "order")


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ("title", "title_en", "section", "parent", "is_active")
    list_filter = ("section", "is_active")
    search_fields = ("title", "title_en", "section__title")
    ordering = ("section__order", "order", "title")
    exclude = ("slug", "order")


@admin.register(ContentSection)
class ContentSectionAdmin(SortableAdminMixin, SortableAdminBase, admin.ModelAdmin):
    form = ContentSectionAdminForm
    list_display = (
        "title",
        "title_en",
        "section",
        "category",
        "parent_section",
        "is_active",
        "map_areas_quick_link",
    )
    list_filter = ("section", "category", "is_active")
    search_fields = ("title", "title_en", "content", "content_en")
    ordering = ("order", "title")
    inlines = (MediaInline, MapComparisonInline, MapAreaInfoInline)
    readonly_fields = ("map_areas_shortcut",)
    fieldsets = (
        (
            "Conteúdo",
            {
                "classes": (
                    "baton-tabs-init",
                    "baton-tab-inline-media",
                    "baton-tab-inline-comparisons",
                    "baton-tab-inline-map-areas",
                ),
                "fields": (
                    "section",
                    "category",
                    "parent_section",
                    "title",
                    "title_en",
                    "content",
                    "content_en",
                    "is_active",
                    "map_areas_shortcut",
                ),
            },
        ),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            # Group each record by its parent when present, otherwise by itself.
            tree_group_id=Coalesce("parent_section_id", "id"),
            # Ensure parent rows are listed before child rows inside each group.
            is_child=Case(
                When(parent_section__isnull=True, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            ),
            # If child, use parent order as primary local sort.
            parent_order=Coalesce("parent_section__order", F("order")),
        ).order_by(
            "section__order",
            "category__order",
            "tree_group_id",
            "is_child",
            "parent_order",
            "order",
            "id",
        ).prefetch_related("map_areas")

    def map_areas_quick_link(self, obj):
        count = obj.map_areas.count()
        changelist_url = f"{reverse('admin:app_mapareainfo_changelist')}?{urlencode({'content__id__exact': obj.id})}"
        return format_html('<a href="{}">Áreas do mapa ({})</a>', changelist_url, count)

    map_areas_quick_link.short_description = "Mapa"

    def map_areas_shortcut(self, obj):
        if not obj or not obj.pk:
            return "Guarde este conteúdo para gerir áreas do mapa."
        changelist_url = f"{reverse('admin:app_mapareainfo_changelist')}?{urlencode({'content__id__exact': obj.id})}"
        add_url = f"{reverse('admin:app_mapareainfo_add')}?{urlencode({'content': obj.id})}"
        return format_html(
            '<a class="button" href="{}" style="margin-right:8px;">Gerir áreas do mapa</a>'
            '<a class="button" href="{}">Adicionar área</a>',
            changelist_url,
            add_url,
        )

    map_areas_shortcut.short_description = "Atalho de áreas do mapa"


@admin.register(MapComparison)
class MapComparisonAdmin(admin.ModelAdmin):
    list_display = ("title", "content", "order")
    search_fields = ("title",)
    ordering = ("content", "order", "id")


@admin.register(Geopark)
class GeoparkAdmin(admin.ModelAdmin):
    list_display = ("name", "name_en", "latitude", "longitude", "date_added", "area_km2", "population")
    search_fields = ("name", "name_en")
    list_filter = ("date_added",)
    ordering = ("name",)
    fieldsets = (
        ("Identificação", {"fields": ("name", "name_en", "date_added")}),
        ("Localização", {"fields": ("latitude", "longitude", "area_km2", "population")}),
        ("Descrição", {"fields": ("description_pt", "description_en", "quote_pt", "quote_en")}),
    )


@admin.register(MapAreaInfo)
class MapAreaInfoAdmin(SortableAdminMixin, admin.ModelAdmin):
    form = MapAreaInfoAdminForm
    list_display = ("title", "location", "area_ha", "fill_color", "content")
    search_fields = ("title", "location", "content__title")
    list_filter = ("content__section",)
    ordering = ("content", "legend_order", "id")
    sortable_field_name = "legend_order"
