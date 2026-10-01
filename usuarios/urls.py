from django.urls import path

from .views import auth, perfil, recuperacion, roles, usuarios

app_name = 'usuarios'

urlpatterns = [
    # ── Sesión ────────────────────────────────────────────────────
    path('login/', auth.LoginView.as_view(), name='login'),
    path('logout/', auth.LogoutView.as_view(), name='logout'),

    # ── Recuperar contraseña (sin sesión) ─────────────────────────
    path('recuperar/', recuperacion.solicitar, name='recuperar'),
    path('recuperar/codigo/', recuperacion.verificar, name='recuperar_codigo'),
    path('recuperar/nueva/', recuperacion.nueva_password, name='recuperar_nueva'),

    # ── Mi perfil ─────────────────────────────────────────────────
    path('mi-perfil/', perfil.ver, name='perfil'),
    path('mi-perfil/editar/', perfil.editar, name='perfil_editar'),
    path('mi-perfil/contrasena/', perfil.cambiar_password, name='cambiar_password'),

    # ── Gestión de usuarios ───────────────────────────────────────
    path('usuarios/', usuarios.lista, name='lista'),
    path('usuarios/nuevo/', usuarios.crear, name='crear'),
    path('usuarios/<int:pk>/', usuarios.detalle, name='detalle'),
    path('usuarios/<int:pk>/editar/', usuarios.editar, name='editar'),
    path('usuarios/<int:pk>/estado/', usuarios.cambiar_estado, name='cambiar_estado'),
    path('usuarios/<int:pk>/contrasena/', usuarios.restablecer_password, name='restablecer_password'),
    path('usuarios/<int:pk>/eliminar/', usuarios.eliminar, name='eliminar'),
    path('usuarios/<int:pk>/permisos/', usuarios.permisos, name='permisos'),

    # ── Roles ─────────────────────────────────────────────────────
    path('roles/', roles.lista, name='roles_lista'),
    path('roles/nuevo/', roles.crear, name='roles_crear'),
    path('roles/<int:pk>/', roles.editar, name='roles_editar'),
    path('roles/<int:pk>/eliminar/', roles.eliminar, name='roles_eliminar'),
]
