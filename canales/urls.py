from django.urls import path

from . import views

app_name = 'canales'

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('verificar/', views.verificar, name='verificar'),
]
