from django.contrib import admin

from .models import VersionApp


@admin.register(VersionApp)
class VersionAppAdmin(admin.ModelAdmin):
    list_display = ['version', 'publicada', 'subida', 'subida_por']
    list_filter = ['publicada']
