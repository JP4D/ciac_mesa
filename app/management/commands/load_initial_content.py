import re
import shutil
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from PIL import Image

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from app.models import Category, ContentSection, Media, SubCategory


W_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
THUMBNAIL_MAX_EDGE = 1920


SECTION_SPECS = [
    {
        "key": "1-enquadramento",
        "title": "1 - Enquadramento Historico do Uso dos Solos",
        "slug": "enquadramento-historico-uso-solos",
        "marker": r"^1\s*-\s*Enquadramento Historico do Uso dos Solos$",
        "folder": "1. Enquadramento Hist Uso Solos",
        "category": ("Enquadramento Historico", "enquadramento-historico", 1),
        "subcategory": ("Uso dos Solos", "uso-dos-solos", 1),
    },
    {
        "key": "1-1-uso-solos",
        "title": "1.1 - Uso dos solos",
        "slug": "uso-dos-solos",
        "marker": r"^1\.1\s*[–-]\s*Uso dos solos$",
        "folder": None,
        "category": ("Enquadramento Historico", "enquadramento-historico", 1),
        "subcategory": ("Uso dos Solos", "uso-dos-solos", 1),
    },
    {
        "key": "2-eutrofizacao",
        "title": "2 - Eutrofizacao",
        "slug": "eutrofizacao",
        "marker": r"^2\s*[–-]\s*Eutrofizacao$",
        "folder": None,
        "category": ("Eutrofizacao", "eutrofizacao", 2),
        "subcategory": ("Contexto", "contexto", 0),
    },
    {
        "key": "2-1-lagoa",
        "title": "2.1 - Lagoa das Furnas",
        "slug": "lagoa-das-furnas",
        "marker": r"^2\.1\s*[–-]\s*Lagoa das Furnas$",
        "folder": "2.1 Lagoa das Furnas",
        "category": ("Eutrofizacao", "eutrofizacao", 2),
        "subcategory": ("Lagoa das Furnas", "lagoa-das-furnas", 1),
    },
    {
        "key": "2-2-causas",
        "title": "2.2 - Principais causas da eutrofizacao",
        "slug": "principais-causas",
        "marker": r"^2\.2\s*[–-]\s*Principais causas da eutrofizacao$",
        "folder": "2.2 causas eutrofizacao",
        "category": ("Eutrofizacao", "eutrofizacao", 2),
        "subcategory": ("Causas", "causas", 2),
    },
    {
        "key": "2-3-consequencias",
        "title": "2.3 - Principais consequencias",
        "slug": "principais-consequencias",
        "marker": r"^2\.3\s*[–-]\s*Principais consequencias EUTROFIZACAO$",
        "folder": "2.3 consequencias eutrofizacao",
        "category": ("Eutrofizacao", "eutrofizacao", 2),
        "subcategory": ("Consequencias", "consequencias", 3),
    },
    {
        "key": "3-0-surgimento",
        "title": "3.0 - Surgimento do Plano",
        "slug": "surgimento-do-plano",
        "marker": r"^(3\s*[–-]\s*)?O surgimento do Plano de Ordenamento da Bacia Hidrografica da Lagoa das Furnas - POBHLF:",
        "folder": "3. o surgimento do Plano",
        "category": ("POBHLF", "pobhlf", 3),
        "subcategory": ("Surgimento do Plano", "surgimento-do-plano", 1),
    },
    {
        "key": "3-1-mapas",
        "title": "3.1 - Mapas de sintese e condicionantes",
        "slug": "mapas-sintese-condicionantes",
        "marker": r"^3\.1\s*[–-]\s*Mapas de sintese e condicionantes$",
        "folder": "3.1 POBHLF_mapas",
        "category": ("POBHLF", "pobhlf", 3),
        "subcategory": ("Mapas", "mapas", 2),
    },
    {
        "key": "3-2-linhas",
        "title": "3.2 - Linhas de orientacao do POBHLF",
        "slug": "linhas-orientacao",
        "marker": r"^3\.2\s*[–-]\s*Linhas de orientacao do POBHLF$",
        "folder": "3.2 linhas orientacao",
        "category": ("POBHLF", "pobhlf", 3),
        "subcategory": ("Linhas de orientacao", "linhas-orientacao", 3),
    },
    {
        "key": "3-3-acao",
        "title": "3.3 - Do papel a acao",
        "slug": "do-papel-a-acao",
        "marker": r"^3\.3\s*-\s*Do papel a acao$",
        "folder": None,
        "category": ("POBHLF", "pobhlf", 3),
        "subcategory": ("Do papel a acao", "do-papel-a-acao", 4),
    },
    {
        "key": "3-3-1-preventivas",
        "title": "3.3.1 - Medidas preventivas",
        "slug": "medidas-preventivas",
        "marker": r"^3\.3\.1\s*-\s*Medidas preventivas$",
        "folder": "3.3.1_medidas preventivas",
        "category": ("POBHLF", "pobhlf", 3),
        "subcategory": ("Do papel a acao", "do-papel-a-acao", 4),
        "parent_key": "3-3-acao",
    },
    {
        "key": "3-3-1-a-aquisicao",
        "title": "A - Aquisição de terrenos",
        "slug": "aquisicao-de-terrenos",
        "marker": r"^a\s*[–-]\s*Aquisicao de terrenos$",
        "folder": None,
        "category": ("POBHLF", "pobhlf", 3),
        "subcategory": ("Do papel a acao", "do-papel-a-acao", 4),
        "parent_key": "3-3-1-preventivas",
    },
    {
        "key": "3-3-1-b-requalificacao",
        "title": "B - Requalificação da paisagem",
        "slug": "requalificacao-da-paisagem",
        "marker": r"^B\s*[–-]\s*Requalificacao da paisagem$",
        "folder": None,
        "category": ("POBHLF", "pobhlf", 3),
        "subcategory": ("Do papel a acao", "do-papel-a-acao", 4),
        "parent_key": "3-3-1-preventivas",
    },
    {
        "key": "3-3-1-c-combate",
        "title": "C - Combate à flora invasora",
        "slug": "combate-a-flora-invasora",
        "marker": r"^C\.?\s*[–-]?\s*Combate a flora invasora$",
        "folder": None,
        "category": ("POBHLF", "pobhlf", 3),
        "subcategory": ("Do papel a acao", "do-papel-a-acao", 4),
        "parent_key": "3-3-1-preventivas",
    },
    {
        "key": "3-3-1-d-restituicao",
        "title": "D - Restituição de flora nativa",
        "slug": "restituicao-de-flora-nativa",
        "marker": r"^D\s*[–-]\s*Restituicao de flora nativa$",
        "folder": None,
        "category": ("POBHLF", "pobhlf", 3),
        "subcategory": ("Do papel a acao", "do-papel-a-acao", 4),
        "parent_key": "3-3-1-preventivas",
    },
    {
        "key": "3-3-2-engenharia",
        "title": "3.3.2 - Engenharia verde",
        "slug": "engenharia-verde",
        "marker": r"^3\.3\.2\s*[–-]\s*Engenharia verde$",
        "folder": "3.3.2 engenharia verde",
        "category": ("POBHLF", "pobhlf", 3),
        "subcategory": ("Do papel a acao", "do-papel-a-acao", 4),
        "parent_key": "3-3-acao",
    },
    {
        "key": "3-3-2-a-linhas",
        "title": "A - Linhas de erosão",
        "slug": "linhas-de-erosao",
        "marker": r"^A\s*[–-]\s*Linhas de erosao$",
        "folder": None,
        "category": ("POBHLF", "pobhlf", 3),
        "subcategory": ("Do papel a acao", "do-papel-a-acao", 4),
        "parent_key": "3-3-2-engenharia",
    },
    {
        "key": "3-3-2-b-dissipadores",
        "title": "B - Dissipadores de energia",
        "slug": "dissipadores-de-energia",
        "marker": r"^B\s*[–-]\s*Dissipadores de energia$",
        "folder": None,
        "category": ("POBHLF", "pobhlf", 3),
        "subcategory": ("Do papel a acao", "do-papel-a-acao", 4),
        "parent_key": "3-3-2-engenharia",
    },
    {
        "key": "3-3-2-c-bacias",
        "title": "C - Bacias de retenção de caudal sólido",
        "slug": "bacias-retencao-caudal-solido",
        "marker": r"^c\s*[–-]\s*Bacias de retencao de caudal solido$",
        "folder": None,
        "category": ("POBHLF", "pobhlf", 3),
        "subcategory": ("Do papel a acao", "do-papel-a-acao", 4),
        "parent_key": "3-3-2-engenharia",
    },
    {
        "key": "3-3-3-gestao",
        "title": "3.3.3 - Gestao sustentavel das atuais pastagens/prados publicos",
        "slug": "gestao-sustentavel",
        "marker": r"^3\.3\.3\s*[–-]\s*Gestao sustentavel",
        "folder": "3.3.3 gestao sustentavel",
        "category": ("POBHLF", "pobhlf", 3),
        "subcategory": ("Do papel a acao", "do-papel-a-acao", 4),
        "parent_key": "3-3-acao",
    },
    {
        "key": "3-3-4-laboratorio",
        "title": "3.3.4 - Laboratorio de paisagem",
        "slug": "laboratorio-paisagem",
        "marker": r"^3\.3\.4\s*[–-]\s*Laboratorio de paisagem$",
        "folder": "3.3.4 laboratorio paisagem",
        "category": ("POBHLF", "pobhlf", 3),
        "subcategory": ("Do papel a acao", "do-papel-a-acao", 4),
        "parent_key": "3-3-acao",
    },
    {
        "key": "3-3-4-1-parceiros",
        "title": "3.3.4.1 - Parceiros e projetos",
        "slug": "parceiros-e-projetos",
        "marker": r"^3\.3\.4\.1\s*[–-]\s*Parceiros e projetos$",
        "folder": None,
        "category": ("POBHLF", "pobhlf", 3),
        "subcategory": ("Do papel a acao", "do-papel-a-acao", 4),
        "parent_key": "3-3-4-laboratorio",
    },
    {
        "key": "3-4-planos",
        "title": "3.4 - Planos de Ordenamento de Bacias Hidrograficas de Lagoa - Acores",
        "slug": "planos-acores",
        "marker": r"^3\.4\s*[–-]\s*Planos de Ordenamento de Bacias Hidrograficas de Lagoa - Acores$",
        "folder": "3.4 Planos açores",
        "category": ("POBHLF", "pobhlf", 3),
        "subcategory": ("Planos Acores", "planos-acores", 5),
    },
]


def strip_accents(value: str) -> str:
    return (
        value.replace("á", "a")
        .replace("à", "a")
        .replace("â", "a")
        .replace("ã", "a")
        .replace("ç", "c")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("Á", "A")
        .replace("À", "A")
        .replace("Â", "A")
        .replace("Ã", "A")
        .replace("Ç", "C")
        .replace("É", "E")
        .replace("Ê", "E")
        .replace("Í", "I")
        .replace("Ó", "O")
        .replace("Ô", "O")
        .replace("Õ", "O")
        .replace("Ú", "U")
    )


def normalize_line(value: str) -> str:
    value = strip_accents(value.strip())
    value = re.sub(r"\s+", " ", value)
    return value


def extract_paragraphs_from_docx(docx_path: Path) -> list[str]:
    with zipfile.ZipFile(docx_path) as archive:
        xml_content = archive.read("word/document.xml")
    root = ET.fromstring(xml_content)

    paragraphs = []
    for paragraph in root.findall(".//w:p", W_NS):
        texts = [node.text for node in paragraph.findall(".//w:t", W_NS) if node.text]
        merged = "".join(texts).strip()
        if merged:
            paragraphs.append(merged)
    return paragraphs


def extract_paragraphs_from_text(text_path: Path) -> list[str]:
    content = text_path.read_text(encoding="utf-8")
    return [line.strip() for line in content.splitlines() if line.strip()]


def section_content_from_paragraphs(paragraphs: list[str]) -> dict[str, str]:
    index_map = {}
    normalized = [normalize_line(item) for item in paragraphs]

    for spec in SECTION_SPECS:
        pattern = re.compile(spec["marker"], re.IGNORECASE)
        for idx, line in enumerate(normalized):
            if pattern.search(line):
                index_map[spec["key"]] = idx
                break

    ordered_keys = [
        item["key"]
        for item in sorted(
            (spec for spec in SECTION_SPECS if spec["key"] in index_map),
            key=lambda x: index_map[x["key"]],
        )
    ]

    content_map: dict[str, str] = {}
    for i, key in enumerate(ordered_keys):
        start_idx = index_map[key] + 1
        end_idx = len(paragraphs)
        if i + 1 < len(ordered_keys):
            end_idx = index_map[ordered_keys[i + 1]]

        section_lines = [line.strip() for line in paragraphs[start_idx:end_idx] if line.strip()]
        content_map[key] = "\n\n".join(section_lines)

    return content_map


def generate_display_thumbnail(source_abs_path: Path, media_root: Path, target_rel_path: Path) -> str:
    """
    Generate a display thumbnail preserving aspect ratio.
    The longest edge is capped at THUMBNAIL_MAX_EDGE and no upscaling is performed.
    Returns media-relative thumbnail path.
    """
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
            # Keep compatibility by storing as JPEG for uncommon formats.
            thumb_abs_path = thumb_abs_path.with_suffix(".jpg")
            thumb_rel_path = thumb_rel_path.with_suffix(".jpg")
            img.save(thumb_abs_path, optimize=True, quality=88, progressive=True)

    return str(thumb_rel_path)


class Command(BaseCommand):
    help = "Load initial content from project DOCX and section image folders."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Allow import when data already exists (dangerous).",
        )
        parser.add_argument(
            "--text-file",
            default=str(Path(settings.BASE_DIR).parent / "data" / "conteudo_text_only.txt"),
            help="Path to plain text source file. Used when available.",
        )
        parser.add_argument(
            "--docx",
            default=str(
                Path(settings.BASE_DIR).parent
                / "data"
                / "Conteudo_POBHLF_pvalidacao_DGA 20240628_CF_JPV_FINAL.docx"
            ),
            help="Path to source DOCX content file.",
        )
        parser.add_argument(
            "--images-root",
            default=str(Path(settings.BASE_DIR).parent / "data" / "fotos_imagens"),
            help="Path to image root folder.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing app content before import.",
        )

    def handle(self, *args, **options):
        text_file_path = Path(options["text_file"]).expanduser().resolve()
        docx_path = Path(options["docx"]).expanduser().resolve()
        images_root = Path(options["images_root"]).expanduser().resolve()
        force = options["force"]

        if not text_file_path.exists() and not docx_path.exists():
            raise CommandError(f"DOCX file not found: {docx_path}")
        if not images_root.exists():
            raise CommandError(f"Images root not found: {images_root}")

        existing_counts = {
            "categories": Category.objects.count(),
            "subcategories": SubCategory.objects.count(),
            "sections": ContentSection.objects.count(),
            "media": Media.objects.count(),
        }
        has_existing_data = any(existing_counts.values())
        if has_existing_data and not force:
            raise CommandError(
                "Import blocked to protect manual edits. Existing data found: "
                f"{existing_counts}. "
                "If you intentionally want to run this importer, rerun with --force."
            )

        if options["reset"]:
            self.stdout.write("Reset flag enabled: deleting existing content data...")
            Media.objects.all().delete()
            ContentSection.objects.all().delete()
            SubCategory.objects.all().delete()
            Category.objects.all().delete()

        if text_file_path.exists():
            self.stdout.write(f"Using text source file: {text_file_path}")
            paragraphs = extract_paragraphs_from_text(text_file_path)
        else:
            self.stdout.write(f"Using DOCX source file: {docx_path}")
            paragraphs = extract_paragraphs_from_docx(docx_path)
        content_map = section_content_from_paragraphs(paragraphs)

        categories: dict[str, Category] = {}
        subcategories: dict[tuple[str, str], SubCategory] = {}
        sections: dict[str, ContentSection] = {}

        for spec in SECTION_SPECS:
            cat_title, cat_slug, cat_order = spec["category"]
            category, _ = Category.objects.get_or_create(
                slug=cat_slug,
                defaults={
                    "title": cat_title,
                    "title_en": "",
                    "order": cat_order,
                    "is_active": True,
                },
            )
            categories[cat_slug] = category

            sub_title, sub_slug, sub_order = spec["subcategory"]
            sub_key = (cat_slug, sub_slug)
            if sub_key not in subcategories:
                subcategory, _ = SubCategory.objects.get_or_create(
                    section=category,
                    parent=None,
                    slug=sub_slug,
                    defaults={
                        "title": sub_title,
                        "title_en": "",
                        "order": sub_order,
                        "is_active": True,
                    },
                )
                subcategories[sub_key] = subcategory

        for order, spec in enumerate(SECTION_SPECS, start=1):
            cat_slug = spec["category"][1]
            sub_slug = spec["subcategory"][1]
            top_section = categories[cat_slug]
            subcategory = subcategories[(cat_slug, sub_slug)]
            parent = sections.get(spec.get("parent_key"))
            content = content_map.get(spec["key"], "").strip()

            content_entry, _ = ContentSection.objects.update_or_create(
                section=top_section,
                category=subcategory,
                parent_section=parent,
                slug=spec["slug"],
                defaults={
                    "title": spec["title"],
                    "title_en": "",
                    "content": content,
                    "content_en": "",
                    "order": order,
                    "is_active": True,
                },
            )
            sections[spec["key"]] = content_entry

        media_root = Path(settings.MEDIA_ROOT)
        media_root.mkdir(parents=True, exist_ok=True)

        imported_media = 0
        for spec in SECTION_SPECS:
            folder_name = spec.get("folder")
            if not folder_name:
                continue

            content_entry = sections[spec["key"]]
            content_entry.media.all().delete()
            # Special split: first section has mixed images where "Uso do solo"
            # belongs to 1.1, not the parent intro section.
            if spec["key"] == "1-enquadramento" and "1-1-uso-solos" in sections:
                sections["1-1-uso-solos"].media.all().delete()

            source_dir = images_root / folder_name
            if not source_dir.exists():
                self.stdout.write(
                    self.style.WARNING(f"Image folder missing for section: {folder_name}")
                )
                continue

            allowed_ext = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
            files = sorted(
                [
                    path
                    for path in source_dir.iterdir()
                    if path.is_file() and path.suffix.lower() in allowed_ext
                ]
            )
            section_order_counters = {
                spec["key"]: 0,
                "1-1-uso-solos": 0,
            }

            for source_file in files:
                target_rel_dir = Path("source_assets") / folder_name
                target_rel_path = target_rel_dir / source_file.name
                target_abs_path = media_root / target_rel_path
                target_abs_path.parent.mkdir(parents=True, exist_ok=True)

                if not target_abs_path.exists():
                    shutil.copy2(source_file, target_abs_path)

                thumbnail_rel_path = generate_display_thumbnail(
                    source_abs_path=target_abs_path,
                    media_root=media_root,
                    target_rel_path=target_rel_path,
                )

                stem = source_file.stem.replace("_", " ").replace("-", " ").strip()
                caption = re.sub(r"\s+", " ", stem)
                media_type = "map" if "mapa" in folder_name.lower() else "image"

                target_content = content_entry
                target_key = spec["key"]
                if spec["key"] == "1-enquadramento" and "1-1-uso-solos" in sections:
                    file_name_l = source_file.name.lower()
                    if (
                        "uso do solo" in file_name_l
                        or "usosolo" in file_name_l
                        or "alteracaopobhlf" in file_name_l
                    ):
                        target_content = sections["1-1-uso-solos"]
                        target_key = "1-1-uso-solos"
                section_order_counters[target_key] = section_order_counters.get(target_key, 0) + 1

                Media.objects.create(
                    content=target_content,
                    media_type=media_type,
                    file=str(target_rel_path),
                    thumbnail=thumbnail_rel_path,
                    caption=caption[:200],
                    caption_en="",
                    order=section_order_counters[target_key],
                    is_zoomable=(media_type == "image"),
                )
                imported_media += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Initial load completed: "
                f"{Category.objects.count()} categories, "
                f"{SubCategory.objects.count()} subcategories, "
                f"{ContentSection.objects.count()} sections, "
                f"{imported_media} media items."
            )
        )
