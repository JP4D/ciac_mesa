from django.shortcuts import render

from .models import Category, ContentSection
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
                "is_zoomable": media.is_zoomable,
            }
        )
    return media_items


def _serialize_content_tree(content):
    return {
        "id": content.id,
        "title": content.title,
        "title_en": content.title_en,
        "slug": content.slug,
        "content": content.content,
        "content_en": content.content_en,
        "media": _serialize_media(content),
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
            "contents__subsections__media",
            "contents__subsections__subsections__media",
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
            .prefetch_related("media", "subsections__media", "subsections__subsections__media")
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

    default_model_url = "/static/app/models/furnas_10.glb"
    model_path = Path(settings.BASE_DIR) / "app" / "static" / "app" / "models" / "furnas_10.glb"

    context = {
        "sections": sections,
        "model_url": default_model_url if model_path.exists() else "",
    }
    return render(request, "app/index.html", context)
