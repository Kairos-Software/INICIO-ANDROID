"""
Activar o desactivar el modo mantenimiento desde la terminal (por ejemplo,
si no podés entrar al sistema desde el navegador).

    python manage.py mantenimiento estado
    python manage.py mantenimiento activar --mensaje "Actualizando" --vuelve "a las 15:30"
    python manage.py mantenimiento desactivar

El servidor lo nota solo en unos segundos (no hace falta reiniciarlo).
Ojo: si está forzado desde el .env (MODO_MANTENIMIENTO=True), esto no lo
apaga: hay que cambiar el .env y reiniciar el servidor.
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from actividad.models import Accion
from actividad.registro import registrar
from core.models import EstadoMantenimiento


class Command(BaseCommand):
    help = 'Activa, desactiva o muestra el estado del modo mantenimiento.'

    def add_arguments(self, parser):
        parser.add_argument('accion', choices=['activar', 'desactivar', 'estado'])
        parser.add_argument('--mensaje', default=None, help='Mensaje para los usuarios.')
        parser.add_argument('--vuelve', default=None, help='Ej: "a las 15:30".')

    def handle(self, *args, accion, mensaje, vuelve, **options):
        estado = EstadoMantenimiento.obtener()

        if accion != 'estado':
            estado.activo = accion == 'activar'
            if mensaje is not None:
                estado.mensaje = mensaje
            if vuelve is not None:
                estado.vuelve_aprox = vuelve
            estado.modificado_por = None
            estado.save()
            registrar(None, Accion.SISTEMA,
                      f'{"Activó" if estado.activo else "Desactivó"} el modo mantenimiento (desde la terminal)',
                      objeto=estado, modulo='sistema')

        texto = 'ACTIVO' if estado.activo else 'desactivado'
        self.stdout.write(self.style.WARNING(f'Modo mantenimiento: {texto}') if estado.activo
                          else self.style.SUCCESS(f'Modo mantenimiento: {texto}'))
        if getattr(settings, 'MODO_MANTENIMIENTO', False):
            self.stdout.write(self.style.ERROR(
                'Atención: está FORZADO desde el .env (MODO_MANTENIMIENTO=True). '
                'Para salir, cambialo a False y reiniciá el servidor.'
            ))
