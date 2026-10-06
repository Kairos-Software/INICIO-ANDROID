from django.urls import path

from . import views

app_name = 'reventa'

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('mi-pantalla/', views.mi_pantalla, name='mi_pantalla'),
    path('estadisticas/', views.ver_estadisticas, name='estadisticas'),
    path('revendedores/', views.revendedores, name='revendedores'),
    path('revendedores/nuevo/', views.revendedor_nuevo, name='revendedor_nuevo'),
    path('revendedores/<int:pk>/', views.revendedor, name='revendedor'),
    path('revendedores/<int:pk>/accion/', views.revendedor_accion, name='revendedor_accion'),
    path('clientes/', views.clientes, name='clientes'),
    path('clientes/nuevo/', views.cliente_nuevo, name='cliente_nuevo'),
    path('clientes/<int:pk>/', views.cliente, name='cliente'),
    path('clientes/<int:pk>/editar/', views.cliente_editar, name='cliente_editar'),
    path('clientes/<int:pk>/renovar/', views.cliente_renovar, name='cliente_renovar'),
    path('clientes/<int:pk>/codigo/', views.cliente_codigo, name='cliente_codigo'),
    path('clientes/<int:pk>/liberar/', views.cliente_liberar, name='cliente_liberar'),
    path('creditos/', views.creditos, name='creditos'),
    path('creditos/comprar/', views.pedir_compra, name='pedir_compra'),
    path('paquetes/', views.paquetes, name='paquetes'),
    path('paquetes/nuevo/', views.paquete_editar, name='paquete_nuevo'),
    path('paquetes/<int:pk>/', views.paquete_editar, name='paquete_editar'),
    path('compras/', views.compras, name='compras'),
    path('compras/<int:pk>/', views.compra_resolver, name='compra_resolver'),
]
