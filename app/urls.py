from django.urls import path

from .views import api_geoparks, interactive_table


urlpatterns = [
    path("", interactive_table, name="interactive-table"),
    path("api/geoparks/", api_geoparks, name="api-geoparks"),
]
