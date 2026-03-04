import re
import shutil
from pathlib import Path

from PIL import Image
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from app.models import ContentSection, Media

THUMBNAIL_MAX_EDGE = 1920


PROJECT_SPECS = [
    {
        "title": "1. MIT - Green Islands - Biomassa Lenhosa",
        "slug": "mit-green-islands-biomassa-lenhosa",
        "markers": [r"1\.\s*MIT - Green Islands - Biomassa Lenhosa", r"1\.\s*MIT"],
        "file_tokens": ["mit_"],
    },
    {
        "title": "2. PTLogo",
        "slug": "ptlogo",
        "markers": [r"2\.\s*PTLogo"],
        "file_tokens": ["pt_"],
    },
    {
        "title": "3. Pólen das Furnas",
        "slug": "polen-das-furnas",
        "markers": [r"3\.?\s*Pólen das Furnas", r"3\.?\s*Polen das Furnas"],
        "file_tokens": ["polen_"],
    },
    {
        "title": "4. Arboreto do Reinfforce",
        "slug": "arboreto-do-reinfforce",
        "markers": [r"4\.\s*Arboreto do Reinfforce"],
        "file_tokens": ["reinforce_"],
    },
    {
        "title": "5. Floresta SATA",
        "slug": "floresta-sata",
        "markers": [r"5\.?\s*Floresta SATA"],
        "file_tokens": ["sata_"],
    },
    {
        "title": "6. Pomar das Furnas",
        "slug": "pomar-das-furnas",
        "markers": [r"6\.?\s*Pomar das Furnas"],
        "file_tokens": ["pomar_"],
    },
    {
        "title": "7. Plantação de Vimes",
        "slug": "plantacao-de-vimes",
        "markers": [r"7\.?\s*Plantação de Vimes", r"7\.?\s*Plantacao de Vimes"],
        "file_tokens": ["vimes_"],
    },
    {
        "title": "8. Pomares de Sementes",
        "slug": "pomares-de-sementes",
        "markers": [r"8\.?\s*Pomares de Sementes"],
        "file_tokens": ["pomares_"],
    },
    {
        "title": "9. Ilha Avifauna",
        "slug": "ilha-avifauna",
        "markers": [r"9\.?\s*Ilha Avifauna"],
        "file_tokens": ["ilha avifauna"],
    },
    {
        "title": "10. Um projeto social",
        "slug": "um-projeto-social",
        "markers": [r"Um projeto social"],
        "file_tokens": ["projeto social"],
    },
    {
        "title": "11. Educação ambiental",
        "slug": "educacao-ambiental",
        "markers": [r"Educação Ambiental", r"Educação ambiental", r"Educação Ambiental"],
        "file_tokens": ["edu amb"],
    },
]


def generate_display_thumbnail(source_abs_path: Path, media_root: Path, target_rel_path: Path) -> str:
    thumb_rel_path = Path("thumbnails") / f"display_{THUMBNAIL_MAX_EDGE}" / target_rel_path
    thumb_abs_path = media_root / thumb_rel_path
    thumb_abs_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(source_abs_path) as img:
        img = img.convert("RGB") if img.mode not in ("RGB", "L") else img
        img.thumbnail((THUMBNAIL_MAX_EDGE, THUMBNAIL_MAX_EDGE), Image.Resampling.LANCZOS)
        if thumb_abs_path.suffix.lower() in {".jpg", ".jpeg"}:
            img.save(thumb_abs_path, optimize=True, quality=88, progressive=True)
        elif thumb_abs_path.suffix.lower() == ".png":
            img.save(thumb_abs_path, optimize=True)
        else:
            thumb_abs_path = thumb_abs_path.with_suffix(".jpg")
            thumb_rel_path = thumb_rel_path.with_suffix(".jpg")
            img.save(thumb_abs_path, optimize=True, quality=88, progressive=True)
    return str(thumb_rel_path)


def split_project_blocks(text: str):
    starts = []
    for idx, spec in enumerate(PROJECT_SPECS):
        start_idx = None
        for pattern in spec["markers"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                start_idx = match.start()
                break
        if start_idx is None:
            continue
        starts.append((idx, start_idx))

    starts.sort(key=lambda x: x[1])
    blocks = {}
    for pos, (spec_idx, start) in enumerate(starts):
        end = len(text)
        if pos + 1 < len(starts):
            end = starts[pos + 1][1]
        blocks[spec_idx] = text[start:end].strip()
    return blocks


class Command(BaseCommand):
    help = "Create 3.3.4.1 project children and map project media."

    def add_arguments(self, parser):
        parser.add_argument(
            "--media-source",
            default=str(Path(settings.MEDIA_ROOT) / "source_assets" / "3.3.4 laboratorio paisagem"),
            help="Source directory with project images.",
        )

    def handle(self, *args, **options):
        try:
            parent = ContentSection.objects.get(slug="parceiros-e-projetos")
        except ContentSection.DoesNotExist as exc:
            raise CommandError("Section 'parceiros-e-projetos' not found.") from exc

        source_dir = Path(options["media_source"]).expanduser().resolve()
        if not source_dir.exists():
            raise CommandError(f"Project media source does not exist: {source_dir}")

        text = parent.content or ""
        blocks = split_project_blocks(text)

        media_root = Path(settings.MEDIA_ROOT)
        media_root.mkdir(parents=True, exist_ok=True)
        allowed_ext = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
        source_files = [p for p in source_dir.iterdir() if p.is_file() and p.suffix.lower() in allowed_ext]

        created = 0
        total_media = 0

        for order, spec in enumerate(PROJECT_SPECS, start=1):
            block = blocks.get(order - 1, "").strip()
            title = spec["title"]
            section, is_new = ContentSection.objects.get_or_create(
                section=parent.section,
                category=parent.category,
                parent_section=parent,
                slug=spec["slug"],
                defaults={
                    "title": title,
                    "title_en": "",
                    "content": block,
                    "content_en": "",
                    "order": order,
                    "is_active": True,
                },
            )
            if not is_new:
                section.title = title
                section.content = block
                section.order = order
                section.is_active = True
                section.save(update_fields=["title", "content", "order", "is_active"])
            else:
                created += 1

            section.media.all().delete()

            order_media = 1
            tokens = [t.lower() for t in spec["file_tokens"]]
            for source_file in sorted(source_files):
                lower_name = source_file.name.lower()
                if not any(token in lower_name for token in tokens):
                    continue

                rel_dir = Path("media") / "2026" / "03"
                rel_path = rel_dir / source_file.name
                abs_path = media_root / rel_path
                abs_path.parent.mkdir(parents=True, exist_ok=True)
                if not abs_path.exists():
                    shutil.copy2(source_file, abs_path)

                thumb_rel = generate_display_thumbnail(abs_path, media_root, rel_path)
                caption = re.sub(r"\s+", " ", source_file.stem.replace("_", " ").replace("-", " ")).strip()

                Media.objects.create(
                    content=section,
                    media_type="image",
                    file=str(rel_path),
                    thumbnail=thumb_rel,
                    caption=caption[:200],
                    caption_en="",
                    order=order_media,
                    is_zoomable=True,
                )
                order_media += 1
                total_media += 1

        parent.content = ""
        parent.content_en = ""
        parent.save(update_fields=["content", "content_en"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Setup complete. Created {created} project content items, attached {total_media} media files."
            )
        )
