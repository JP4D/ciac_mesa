from django.db import migrations, models
import django.db.models.deletion


def populate_section_from_category(apps, schema_editor):
    ContentSection = apps.get_model("app", "ContentSection")
    for item in ContentSection.objects.select_related("category__section").all():
        if item.category_id and item.section_id is None:
            item.section_id = item.category.section_id
            item.save(update_fields=["section"])


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="title_en",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.RemoveConstraint(
            model_name="subcategory",
            name="uniq_subcategory_slug_per_category",
        ),
        migrations.RenameField(
            model_name="subcategory",
            old_name="category",
            new_name="section",
        ),
        migrations.AddField(
            model_name="subcategory",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="children",
                to="app.subcategory",
            ),
        ),
        migrations.AddField(
            model_name="subcategory",
            name="title_en",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddConstraint(
            model_name="subcategory",
            constraint=models.UniqueConstraint(
                fields=("section", "parent", "slug"),
                name="uniq_subcategory_slug_in_tree",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="contentsection",
            name="uniq_section_slug_in_scope",
        ),
        migrations.RenameField(
            model_name="contentsection",
            old_name="subcategory",
            new_name="category",
        ),
        migrations.AddField(
            model_name="contentsection",
            name="content_en",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="contentsection",
            name="section",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="contents",
                to="app.category",
            ),
        ),
        migrations.AddField(
            model_name="contentsection",
            name="title_en",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.RunPython(populate_section_from_category, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="contentsection",
            constraint=models.UniqueConstraint(
                fields=("section", "category", "parent_section", "slug"),
                name="uniq_section_slug_in_scope",
            ),
        ),
        migrations.RenameField(
            model_name="media",
            old_name="section",
            new_name="content",
        ),
        migrations.RenameField(
            model_name="mapcomparison",
            old_name="section",
            new_name="content",
        ),
    ]
