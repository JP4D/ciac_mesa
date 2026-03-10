import re

from django.core.management.base import BaseCommand, CommandError

from app.models import ContentSection, Media


ISLAND_SPECS = [
    {
        "title": "Flores",
        "slug": "flores",
        "order": 1,
        "prefixes": ("flores_",),
    },
    {
        "title": "Pico",
        "slug": "pico",
        "order": 2,
        "prefixes": ("pico_",),
    },
    {
        "title": "São Miguel",
        "slug": "sao-miguel",
        "order": 3,
        "prefixes": ("smi_", "smg_", "sao-miguel_", "sao_miguel_"),
    },
]


def split_by_islands(text: str):
    normalized = text or ""
    markers = [
        ("flores", re.search(r"\bFlores\s*:", normalized, flags=re.IGNORECASE)),
        ("pico", re.search(r"\bPico\s*:", normalized, flags=re.IGNORECASE)),
        ("sao-miguel", re.search(r"\bSão Miguel\s*:|\bSao Miguel\s*:", normalized, flags=re.IGNORECASE)),
    ]
    starts = [(key, m.start()) for key, m in markers if m]
    starts.sort(key=lambda x: x[1])
    if not starts:
        return {"intro": normalized.strip(), "blocks": {}}

    intro = normalized[: starts[0][1]].strip()
    blocks = {}
    for idx, (key, start) in enumerate(starts):
        end = len(normalized)
        if idx + 1 < len(starts):
            end = starts[idx + 1][1]
        blocks[key] = normalized[start:end].strip()
    return {"intro": intro, "blocks": blocks}


class Command(BaseCommand):
    help = "Split 3.4 content into Flores/Pico/Sao Miguel children and map media."

    def handle(self, *args, **options):
        try:
            parent = ContentSection.objects.get(slug="planos-acores")
        except ContentSection.DoesNotExist as exc:
            raise CommandError("Section 'planos-acores' not found.") from exc

        split = split_by_islands(parent.content or "")
        parent.content = split["intro"]
        parent.save(update_fields=["content"])

        created = 0
        for spec in ISLAND_SPECS:
            island, is_new = ContentSection.objects.get_or_create(
                section=parent.section,
                category=parent.category,
                parent_section=parent,
                slug=spec["slug"],
                defaults={
                    "title": spec["title"],
                    "title_en": "",
                    "content": split["blocks"].get(spec["slug"], ""),
                    "content_en": "",
                    "order": spec["order"],
                    "is_active": True,
                },
            )
            if is_new:
                created += 1
            else:
                island.title = spec["title"]
                island.content = split["blocks"].get(spec["slug"], "")
                island.order = spec["order"]
                island.is_active = True
                island.save(update_fields=["title", "content", "order", "is_active"])

        children_by_slug = {c.slug: c for c in parent.subsections.all()}
        # Reset media on island children to keep idempotent behavior.
        for child in children_by_slug.values():
            child.media.all().delete()

        parent_media = list(parent.media.order_by("order", "id"))
        moved = 0
        counters = {"flores": 0, "pico": 0, "sao-miguel": 0}
        for media in parent_media:
            name = (media.file.name or "").split("/")[-1].lower()
            target_slug = None
            for spec in ISLAND_SPECS:
                if any(name.startswith(prefix) for prefix in spec["prefixes"]):
                    target_slug = spec["slug"]
                    break
            if not target_slug:
                continue

            target = children_by_slug.get(target_slug)
            if not target:
                continue
            counters[target_slug] += 1
            Media.objects.create(
                content=target,
                media_type=media.media_type,
                file=media.file.name,
                thumbnail=media.thumbnail.name if media.thumbnail else "",
                caption=media.caption,
                caption_en=media.caption_en,
                order=counters[target_slug],
                is_zoomable=media.is_zoomable,
            )
            moved += 1

        # Remove media from parent after reassignment.
        parent.media.all().delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Setup complete. Created {created} island items, moved {moved} media items."
            )
        )
