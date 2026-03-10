from django import forms
from django_ckeditor_5.widgets import CKEditor5Widget

from .models import ContentSection, MapAreaInfo


class ContentSectionAdminForm(forms.ModelForm):
    class Meta:
        model = ContentSection
        fields = "__all__"
        widgets = {
            "content": CKEditor5Widget(config_name="default"),
            "content_en": CKEditor5Widget(config_name="default"),
        }


class MapAreaInfoAdminForm(forms.ModelForm):
    class Meta:
        model = MapAreaInfo
        fields = "__all__"
        widgets = {
            "legend_order": forms.HiddenInput(),
        }
