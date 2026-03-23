"""
Translate all Portuguese text fields to English using Google Translate (free tier).
Only fills fields that are currently blank. Use --force to overwrite existing EN content.
"""

import time
from django.core.management.base import BaseCommand
from deep_translator import GoogleTranslator

translator = GoogleTranslator(source="pt", target="en")


def translate(text):
    if not text or not text.strip():
        return ""
    try:
        result = translator.translate(text.strip())
        time.sleep(0.3)  # stay well under rate limits
        return result or ""
    except Exception as exc:
        print(f"    ⚠ translation error: {exc}")
        return ""


class Command(BaseCommand):
    help = "Fill EN fields by translating from PT (blank fields only, unless --force)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing EN content",
        )

    def handle(self, *args, **options):
        from app.models import Category, SubCategory, ContentSection, Media

        force = options["force"]

        def needs(val):
            return force or not (val or "").strip()

        # ── Category ──────────────────────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING("\nCategories"))
        for obj in Category.objects.all():
            if needs(obj.title_en) and obj.title:
                self.stdout.write(f"  {obj.title[:60]}")
                obj.title_en = translate(obj.title)
                obj.save(update_fields=["title_en"])

        # ── SubCategory ───────────────────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING("\nSubCategories"))
        for obj in SubCategory.objects.all():
            if needs(obj.title_en) and obj.title:
                self.stdout.write(f"  {obj.title[:60]}")
                obj.title_en = translate(obj.title)
                obj.save(update_fields=["title_en"])

        # ── ContentSection ────────────────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING("\nContent sections"))
        for obj in ContentSection.objects.all():
            dirty = []
            if needs(obj.title_en) and obj.title:
                self.stdout.write(f"  title: {obj.title[:60]}")
                obj.title_en = translate(obj.title)
                dirty.append("title_en")
            if needs(obj.content_en) and obj.content and obj.content.strip():
                self.stdout.write(f"  content: {obj.title[:40]}…")
                obj.content_en = translate(obj.content)
                dirty.append("content_en")
            if dirty:
                obj.save(update_fields=dirty)

        # ── Media captions ────────────────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING("\nMedia captions"))
        for obj in Media.objects.exclude(caption="").filter(caption__isnull=False):
            if needs(obj.caption_en):
                self.stdout.write(f"  {obj.caption[:60]}")
                obj.caption_en = translate(obj.caption)
                obj.save(update_fields=["caption_en"])

        self.stdout.write(self.style.SUCCESS("\nDone!"))
