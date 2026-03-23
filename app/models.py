from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    """Top-level section (Secao)."""

    title = models.CharField("Titulo", max_length=200)
    title_en = models.CharField("Titulo (EN)", max_length=200, blank=True)
    slug = models.SlugField("Slug", unique=True, blank=True)
    order = models.PositiveIntegerField("Ordem", default=0)
    icon = models.CharField("Icone", max_length=50, blank=True)
    is_active = models.BooleanField("Ativo", default=True)

    class Meta:
        ordering = ["order", "title"]
        verbose_name = "Secção"
        verbose_name_plural = "Secções"

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title) or "secao"
            candidate = base_slug
            idx = 2
            while Category.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base_slug}-{idx}"
                idx += 1
            self.slug = candidate
        super().save(*args, **kwargs)


class SubCategory(models.Model):
    """Category tree node inside a section."""

    section = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="categories",
        verbose_name="Secção",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="children",
        null=True,
        blank=True,
        verbose_name="Categoria pai",
    )
    title = models.CharField("Titulo", max_length=200)
    title_en = models.CharField("Titulo (EN)", max_length=200, blank=True)
    slug = models.SlugField("Slug", blank=True)
    order = models.PositiveIntegerField("Ordem", default=0)
    is_active = models.BooleanField("Ativo", default=True)

    class Meta:
        ordering = ["order", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=["section", "parent", "slug"],
                name="uniq_subcategory_slug_in_tree",
            )
        ]
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"

    def __str__(self) -> str:
        return f"{self.section.title} / {self.title}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title) or "categoria"
            candidate = base_slug
            idx = 2
            conflict_qs = SubCategory.objects.filter(
                section=self.section,
                parent=self.parent,
                slug=candidate,
            )
            while conflict_qs.exclude(pk=self.pk).exists():
                candidate = f"{base_slug}-{idx}"
                idx += 1
                conflict_qs = SubCategory.objects.filter(
                    section=self.section,
                    parent=self.parent,
                    slug=candidate,
                )
            self.slug = candidate
        super().save(*args, **kwargs)


class ContentSection(models.Model):
    """Content entries shown in the UI."""

    section = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="contents",
        verbose_name="Secção",
    )
    category = models.ForeignKey(
        SubCategory,
        on_delete=models.CASCADE,
        related_name="contents",
        null=True,
        blank=True,
        verbose_name="Categoria",
    )
    parent_section = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="subsections",
        null=True,
        blank=True,
        verbose_name="Subcategoria de",
    )
    title = models.CharField("Titulo", max_length=200)
    title_en = models.CharField("Titulo (EN)", max_length=200, blank=True)
    slug = models.SlugField("Slug", blank=True)
    content = models.TextField("Texto (PT)", blank=True)
    content_en = models.TextField("Texto (EN)", blank=True)
    order = models.PositiveIntegerField("Ordem", default=0)
    is_active = models.BooleanField("Ativo", default=True)

    class Meta:
        ordering = ["order", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=["section", "category", "parent_section", "slug"],
                name="uniq_section_slug_in_scope",
            )
        ]
        verbose_name = "Conteúdo"
        verbose_name_plural = "Conteúdos"

    def __str__(self) -> str:
        return self.title

    def get_breadcrumb(self):
        breadcrumb = [self]
        current = self.parent_section
        while current:
            breadcrumb.insert(0, current)
            current = current.parent_section
        return breadcrumb

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title) or "conteudo"
            candidate = base_slug
            idx = 2
            conflict_qs = ContentSection.objects.filter(
                section=self.section,
                category=self.category,
                parent_section=self.parent_section,
                slug=candidate,
            )
            while conflict_qs.exclude(pk=self.pk).exists():
                candidate = f"{base_slug}-{idx}"
                idx += 1
                conflict_qs = ContentSection.objects.filter(
                    section=self.section,
                    category=self.category,
                    parent_section=self.parent_section,
                    slug=candidate,
                )
            self.slug = candidate
        super().save(*args, **kwargs)


class Media(models.Model):
    """Images/videos/maps bound to a content entry."""

    MEDIA_TYPES = [
        ("image", "Imagem"),
        ("video", "Video"),
        ("map", "Mapa"),
    ]

    content = models.ForeignKey(
        ContentSection,
        on_delete=models.CASCADE,
        related_name="media",
        verbose_name="Conteúdo",
    )
    media_type = models.CharField("Tipo de media", max_length=10, choices=MEDIA_TYPES, default="image")
    file = models.FileField("Ficheiro", upload_to="media/%Y/%m/")
    thumbnail = models.FileField("Miniatura", upload_to="thumbnails/display_1920/", blank=True)
    caption = models.CharField("Legenda", max_length=200, blank=True)
    caption_en = models.CharField("Legenda (EN)", max_length=200, blank=True)
    order = models.PositiveIntegerField("Ordem", default=0)
    group = models.CharField(
        "Grupo",
        max_length=10,
        blank=True,
        help_text="Imagens com o mesmo grupo são mostradas em carrossel (ex: A, B, C…)",
    )

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Media"
        verbose_name_plural = "Media"

    def __str__(self) -> str:
        return self.caption or self.file.name



class Geopark(models.Model):
    """UNESCO Global Geopark entry for the world-map app."""

    name = models.CharField("Nome", max_length=300)
    name_en = models.CharField("Nome (EN)", max_length=300, blank=True)
    latitude = models.DecimalField("Latitude", max_digits=10, decimal_places=6)
    longitude = models.DecimalField("Longitude", max_digits=10, decimal_places=6)
    date_added = models.DateField("Data de adesão", null=True, blank=True)
    description_pt = models.TextField("Introdução (PT)", blank=True)
    description_en = models.TextField("Introduction (EN)", blank=True)
    quote_pt = models.CharField("Frase (PT)", max_length=500, blank=True)
    quote_en = models.CharField("Quote (EN)", max_length=500, blank=True)
    area_km2 = models.FloatField("Área (km²)", null=True, blank=True)
    population = models.IntegerField("População", null=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Geoparque"
        verbose_name_plural = "Geoparques"

    def __str__(self) -> str:
        return self.name


class MapAreaInfo(models.Model):
    """Popup data for interactive map overlays bound to a content entry."""

    content = models.ForeignKey(
        ContentSection,
        on_delete=models.CASCADE,
        related_name="map_areas",
        verbose_name="Conteúdo",
    )
    area_index = models.PositiveIntegerField("Indice da área (SVG)", default=0)
    legend_order = models.PositiveIntegerField("Ordem da legenda", default=0)
    title = models.CharField("Designação", max_length=255)
    location = models.CharField("Local", max_length=255, blank=True)
    area_ha = models.DecimalField("Area (ha)", max_digits=12, decimal_places=9, null=True, blank=True)
    fill_color = models.CharField("Cor da área", max_length=32, blank=True, help_text="Hex/RGBA (ex: #34a853)")

    class Meta:
        ordering = ["legend_order", "id"]
        verbose_name = "Área do mapa"
        verbose_name_plural = "Mapa Aquisição"

    def __str__(self) -> str:
        return self.title
