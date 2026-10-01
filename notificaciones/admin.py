from django.contrib import admin

from .models import Notificacion


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('creada', 'destinatario', 'titulo', 'nivel', 'leida_en')
    list_filter = ('nivel',)
    search_fields = ('titulo', 'mensaje', 'destinatario__username')
