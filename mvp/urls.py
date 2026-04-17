from django.contrib import admin
from django.urls import include, path
from django.shortcuts import redirect

urlpatterns = [
    path("", lambda request: redirect("login")),
    path("admin/", admin.site.urls),
    path("", include("game.urls")),
]