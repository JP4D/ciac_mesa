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
    is_zoomable = models.BooleanField("Permite zoom", default=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Media"
        verbose_name_plural = "Media"

    def __str__(self) -> str:
        return self.caption or self.file.name


class MapComparison(models.Model):
    """Before/after map comparison assets for section views."""

    content = models.ForeignKey(
        ContentSection,
        on_delete=models.CASCADE,
        related_name="comparisons",
        verbose_name="Conteúdo",
    )
    title = models.CharField("Titulo", max_length=200)
    image_before = models.ImageField("Imagem antes", upload_to="maps/before/")
    image_after = models.ImageField("Imagem depois", upload_to="maps/after/")
    caption_before = models.CharField("Legenda antes", max_length=100, default="Antes")
    caption_after = models.CharField("Legenda depois", max_length=100, default="Depois")
    order = models.PositiveIntegerField("Ordem", default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Comparação de mapa"
        verbose_name_plural = "Comparações de mapa"

    def __str__(self) -> str:
        return self.title
