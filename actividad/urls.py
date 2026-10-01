from django.urls import path

from . import views

app_name = 'actividad'

urlpatterns = [
    path('', views.lista, name='lista'),
]
