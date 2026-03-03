from django.urls import path

from .views import interactive_table


urlpatterns = [
    path("", interactive_table, name="interactive-table"),
]
