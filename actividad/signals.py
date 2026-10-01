"""
Ingresos, salidas e intentos fallidos: Django avisa con "señales" (signals)
y acá se registran. No hace falta tocar las vistas de login.
"""

from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from .middleware import ip_de_request
from .models import Accion
from .registro import registrar


@receiver(user_logged_in)
def al_ingresar(sender, request, user, **kwargs):
    registrar(user, Accion.INGRESO, 'Ingresó al sistema', modulo='sesion',
              ip=ip_de_request(request) if request else None)


@receiver(user_logged_out)
def al_salir(sender, request, user, **kwargs):
    if user is not None:
        registrar(user, Accion.SALIDA, 'Cerró sesión', modulo='sesion',
                  ip=ip_de_request(request) if request else None)


@receiver(user_login_failed)
def al_fallar_ingreso(sender, credentials, request=None, **kwargs):
    # Nunca se guarda la contraseña: solo lo que escribió como usuario
    identificador = (credentials.get('username') or '')[:100]
    registrar(None, Accion.INGRESO_FALLIDO, f'Intento de ingreso fallido como "{identificador}"',
              modulo='sesion', ip=ip_de_request(request) if request else None)
