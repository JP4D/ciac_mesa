from django.shortcuts import render
from django.http import JsonResponse

from .models import Category, ContentSection, Geopark
from pathlib import Path

from django.conf import settings


def _serialize_media(content):
    media_items = []
    for media in content.media.all().order_by("order", "id"):
        media_items.append(
            {
                "type": media.media_type,
                "url": media.thumbnail.url if media.thumbnail else (media.file.url if media.file else ""),
                "full_url": media.file.url if media.file else "",
                "caption": media.caption,
                "caption_en": media.caption_en,
                "group": media.group,
            }
        )
    return media_items


def _serialize_map_areas(content):
    items = []
    for area in content.map_areas.all().order_by("legend_order", "id"):
        items.append(
            {
                "area_index": area.area_index,
                "legend_order": area.legend_order,
                "title": area.title,
                "location": area.location,
                "area_ha": str(area.area_ha) if area.area_ha is not None else "",
                "fill_color": area.fill_color,
            }
        )
    return items


def _serialize_content_tree(content):
    return {
        "id": content.id,
        "title": content.title,
        "title_en": content.title_en,
        "slug": content.slug,
        "content": content.content,
        "content_en": content.content_en,
        "media": _serialize_media(content),
        "map_areas": _serialize_map_areas(content),
        "children": [
            _serialize_content_tree(child)
            for child in content.subsections.all().order_by("order", "id")
        ],
    }


def interactive_table(request):
    sections = []
    queryset = (
        Category.objects.filter(is_active=True)
        .prefetch_related(
            "contents__media",
            "contents__map_areas",
            "contents__subsections__media",
            "contents__subsections__map_areas",
            "contents__subsections__subsections__media",
            "contents__subsections__subsections__map_areas",
        )
        .order_by("order", "id")
    )

    for section in queryset:
        root_contents = (
            ContentSection.objects.filter(
                section=section,
                parent_section__isnull=True,
                is_active=True,
            )
            .prefetch_related(
                "media",
                "map_areas",
                "subsections__media",
                "subsections__map_areas",
                "subsections__subsections__media",
                "subsections__subsections__map_areas",
            )
            .order_by("order", "id")
        )
        sections.append(
            {
                "id": section.id,
                "slug": section.slug,
                "title": section.title,
                "title_en": section.title_en,
                "contents": [_serialize_content_tree(item) for item in root_contents],
            }
        )

    models_dir = Path(settings.BASE_DIR) / "app" / "static" / "app" / "models"
    if (models_dir / "multic.glb").exists():
        model_url = "/static/app/models/multic.glb"
    elif (models_dir / "furnas_10.glb").exists():
        model_url = "/static/app/models/furnas_10.glb"
    else:
        model_url = ""

    context = {
        "sections": sections,
        "model_url": model_url,
    }
    return render(request, "app/index.html", context)


def api_geoparks(request):
    """GET /api/geoparks/ — returns all geopark records as JSON."""
    parks = list(
        Geopark.objects.values(
            "id",
            "name",
            "name_en",
            "latitude",
            "longitude",
            "date_added",
            "description_pt",
            "description_en",
            "quote_pt",
            "quote_en",
            "area_km2",
            "population",
        )
    )
    # Coerce Decimal to float for JSON serialisation
    for p in parks:
        p["latitude"] = float(p["latitude"])
        p["longitude"] = float(p["longitude"])
        if p["date_added"]:
            p["date_added"] = p["date_added"].isoformat()
    return JsonResponse(parks, safe=False)
