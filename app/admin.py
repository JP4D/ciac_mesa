from django.contrib import admin
from adminsortable2.admin import SortableAdminBase, SortableAdminMixin, SortableInlineAdminMixin, SortableTabularInline
from django.db.models import Case, F, IntegerField, Value, When
from django.db.models.functions import Coalesce
from django.utils.html import format_html
from django.urls import path, reverse
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from urllib.parse import urlencode

from .forms import ContentSectionAdminForm, MapAreaInfoAdminForm
from .models import Category, ContentSection, Geopark, MapAreaInfo, Media, SiteSettings, SubCategory
from .management.commands.import_geoparks import (
    _load_xlsx, _load_csv, _parse_coords, _parse_date,
    _safe_float, _safe_int, HEADER_MAP,
)

admin.site.site_header  = "POBHLF"
admin.site.site_title   = "POBHLF Admin"
admin.site.index_title  = "Gestor de Conteúdos"


class MediaInline(SortableInlineAdminMixin, admin.TabularInline):
    model = Media
    extra = 0
    fields = ("preview", "media_type", "file", "caption", "caption_en", "group")
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
    exclude = ("slug", "order", "icon")


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
    inlines = (MediaInline, MapAreaInfoInline)
    readonly_fields = ("map_areas_shortcut",)
    fieldsets = (
        (
            "Conteúdo",
            {
                "classes": (
                    "baton-tabs-init",
                    "baton-tab-inline-media",
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



@admin.register(Geopark)
class GeoparkAdmin(admin.ModelAdmin):
    list_display = ("name", "name_en", "latitude", "longitude", "date_added", "area_km2", "population")
    search_fields = ("name", "name_en")
    list_filter = ("date_added",)
    ordering = ("name",)
    change_list_template = "admin/app/geopark/change_list.html"
    fieldsets = (
        ("Identificação", {"fields": ("name", "name_en", "date_added")}),
        ("Localização", {"fields": ("latitude", "longitude", "area_km2", "population")}),
        ("Descrição", {"fields": ("description_pt", "description_en", "quote_pt", "quote_en")}),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("import/", self.admin_site.admin_view(self.import_view), name="app_geopark_import"),
        ]
        return custom + urls

    def import_view(self, request):
        result = None

        if request.method == "POST":
            upload = request.FILES.get("import_file")
            force = bool(request.POST.get("force"))

            if not upload:
                result = {"error": "Nenhum ficheiro enviado."}
            else:
                import tempfile, os
                from pathlib import Path
                suffix = Path(upload.name).suffix.lower()
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        for chunk in upload.chunks():
                            tmp.write(chunk)
                        tmp_path = Path(tmp.name)

                    if suffix in (".xlsx", ".xlsm", ".xls"):
                        headers, rows = _load_xlsx(tmp_path)
                    elif suffix == ".csv":
                        headers, rows = _load_csv(tmp_path)
                    else:
                        result = {"error": f"Formato não suportado: {suffix}"}
                        headers = None

                    if headers is not None:
                        col_map = {}
                        for idx, h in enumerate(headers):
                            key = HEADER_MAP.get(h.lower())
                            if key:
                                col_map[key] = idx

                        created = updated = skipped = 0
                        for row in rows:
                            name = str(row[col_map["name"]]).strip() if "name" in col_map and row[col_map["name"]] else ""
                            if not name:
                                continue
                            coords = _parse_coords(row[col_map["coords"]] if "coords" in col_map else None)
                            if not coords:
                                skipped += 1
                                continue
                            lat, lon = coords
                            defaults = {
                                "latitude": lat,
                                "longitude": lon,
                                "name_en": str(row[col_map["name_en"]]).strip() if "name_en" in col_map and row[col_map["name_en"]] else "",
                                "date_added": _parse_date(row[col_map["date_added"]]) if "date_added" in col_map else None,
                                "description_pt": str(row[col_map["description_pt"]]).strip() if "description_pt" in col_map and row[col_map["description_pt"]] else "",
                                "description_en": str(row[col_map["description_en"]]).strip() if "description_en" in col_map and row[col_map["description_en"]] else "",
                                "quote_pt": str(row[col_map["quote_pt"]]).strip() if "quote_pt" in col_map and row[col_map["quote_pt"]] else "",
                                "quote_en": str(row[col_map["quote_en"]]).strip() if "quote_en" in col_map and row[col_map["quote_en"]] else "",
                                "area_km2": _safe_float(row[col_map["area_km2"]] if "area_km2" in col_map else None),
                                "population": _safe_int(row[col_map["population"]] if "population" in col_map else None),
                            }
                            existing = Geopark.objects.filter(name__iexact=name).first()
                            if existing:
                                if force:
                                    for field, value in defaults.items():
                                        setattr(existing, field, value)
                                    existing.save()
                                    updated += 1
                                else:
                                    skipped += 1
                            else:
                                Geopark.objects.create(name=name, **defaults)
                                created += 1

                        result = {"created": created, "updated": updated, "skipped": skipped}

                except Exception as exc:
                    result = {"error": str(exc)}
                finally:
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass

        context = {
            **self.admin_site.each_context(request),
            "title": "Importar Geoparques",
            "result": result,
            "force_default": True,  # "Replace existing" ticked by default
            "opts": self.model._meta,
        }
        return TemplateResponse(request, "admin/app/geopark/import.html", context)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Português", {"fields": ("title_pt", "subtitle_pt")}),
        ("English",   {"fields": ("title_en", "subtitle_en")}),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom = [
            path("", self.admin_site.admin_view(self.singleton_redirect), name="app_sitesettings_changelist"),
        ]
        return custom + urls

    def singleton_redirect(self, request):
        from django.http import HttpResponseRedirect
        obj = SiteSettings.get()
        return HttpResponseRedirect(f"/admin/app/sitesettings/{obj.pk}/change/")


@admin.register(MapAreaInfo)
class MapAreaInfoAdmin(SortableAdminMixin, admin.ModelAdmin):
    form = MapAreaInfoAdminForm
    list_display = ("title", "location", "area_ha", "fill_color", "content")
    search_fields = ("title", "location", "content__title")
    list_filter = ("content__section",)
    ordering = ("content", "legend_order", "id")
    sortable_field_name = "legend_order"
