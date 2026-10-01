"""
Crea los roles iniciales (usuarios/catalogo_permisos.py → ROLES_INICIALES).

    python manage.py crear_roles_iniciales

- Los roles que no existen se crean con sus permisos.
- Los que ya existen NO se pisan (si los editaste desde el sistema, quedan así).
- Excepción: los roles de "todos los permisos" ('*', ej: Administrador)
  reciben los permisos NUEVOS del catálogo. Nunca se les quita ninguno.
  Correrlo después de sumar los permisos de un módulo nuevo.
"""

from django.core.management.base import BaseCommand

from usuarios.servicios import sincronizar_roles_iniciales


class Command(BaseCommand):
    help = 'Crea los roles iniciales y le suma los permisos nuevos a los roles de "todos los permisos".'

    def handle(self, *args, **options):
        for linea in sincronizar_roles_iniciales():
            self.stdout.write(linea)
