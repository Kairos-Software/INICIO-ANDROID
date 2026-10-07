from django.urls import path

from . import views

app_name = 'canales'

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('verificar/lote/', views.verificar_lote, name='verificar_lote'),
    path('importaciones/<int:pk>/', views.importacion, name='importacion'),
    path('importaciones/<int:pk>/lote/', views.importacion_lote, name='importacion_lote'),
    path('importaciones/<int:pk>/cargar/', views.importacion_cargar, name='importacion_cargar'),
    path('importaciones/<int:pk>/reintentar/', views.importacion_reintentar, name='importacion_reintentar'),
    path('importaciones/<int:pk>/borrar/', views.importacion_borrar, name='importacion_borrar'),
    path('catalogo/', views.catalogo, name='catalogo'),
    path('series/', views.series, name='series'),
    path('series/detalle/', views.serie_detalle, name='serie_detalle'),
    path('canal/<int:pk>/editar/', views.canal_editar, name='canal_editar'),
    path('probar/', views.probar, name='probar'),
    path('lo-mas-visto/', views.lo_mas_visto, name='lo_mas_visto'),
    path('limpiar-nombres/', views.limpiar_nombres, name='limpiar_nombres'),
    path('catalogo/quitar/', views.catalogo_quitar, name='catalogo_quitar'),
    path('catalogo/mostrar/', views.catalogo_mostrar, name='catalogo_mostrar'),
]
