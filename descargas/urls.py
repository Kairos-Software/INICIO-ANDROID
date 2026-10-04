from django.urls import path

from . import views

app_name = 'descargas'

urlpatterns = [
    path('descargar/', views.descargar, name='descargar'),
    path('descargar/<int:pk>/', views.descargar, name='descargar_version'),
    path('app-android/', views.pagina, name='pagina'),
    path('app-android/<int:pk>/publicada/', views.cambiar_publicada, name='cambiar_publicada'),
]
