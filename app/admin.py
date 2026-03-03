from django.contrib import admin
from adminsortable2.admin import SortableAdminBase, SortableAdminMixin, SortableInlineAdminMixin

from .forms import ContentSectionAdminForm
from .models import Category, ContentSection, MapComparison, Media, SubCategory


class MediaInline(SortableInlineAdminMixin, admin.TabularInline):
    model = Media
    extra = 0
    fields = ("media_type", "file", "caption", "caption_en", "is_zoomable")
    ordering = ("order", "id")
    sortable_field_name = "order"
    classes = ("baton-tab-inline-media",)


class MapComparisonInline(SortableInlineAdminMixin, admin.TabularInline):
    model = MapComparison
    extra = 0
    fields = ("title", "image_before", "image_after", "caption_before", "caption_after")
    ordering = ("order", "id")
    sortable_field_name = "order"
    classes = ("baton-tab-inline-comparisons",)


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
    list_display = ("title", "title_en", "section", "category", "parent_section", "is_active")
    list_filter = ("section", "category", "is_active")
    search_fields = ("title", "title_en", "content", "content_en")
    ordering = ("order", "title")
    inlines = (MediaInline, MapComparisonInline)
    fieldsets = (
        (
            "Conteúdo",
            {
                "classes": (
                    "baton-tabs-init",
                    "baton-tab-inline-media",
                    "baton-tab-inline-comparisons",
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
                ),
            },
        ),
    )


@admin.register(MapComparison)
class MapComparisonAdmin(admin.ModelAdmin):
    list_display = ("title", "content", "order")
    search_fields = ("title",)
    ordering = ("content", "order", "id")
