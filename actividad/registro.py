"""
Cómo registra actividad cualquier parte del sistema (capa Base).

    from actividad.registro import registrar, cambios_de_formulario
    from actividad.models import Accion

    registrar(request.user, Accion.CREAR, f'Creó el cliente {cliente}', objeto=cliente, modulo='clientes')

    # Al editar, guardando qué cambió:
    registrar(request.user, Accion.EDITAR, f'Editó el cliente {cliente}', objeto=cliente,
              cambios=cambios_de_formulario(form), modulo='clientes')

La IP la toma sola (la deja ContextoActividadMiddleware en cada pedido).
Registrar nunca rompe la operación principal: si falla, lo anota en el log
y sigue.
"""

import contextvars
import logging

from django.db import transaction

from .models import RegistroActividad

logger = logging.getLogger(__name__)

# IP del pedido actual (la completa ContextoActividadMiddleware)
ip_actual = contextvars.ContextVar('actividad_ip', default=None)

# Campos cuyo valor nunca se guarda en `cambios` (solo se anota que cambiaron)
CAMPOS_OCULTOS = {'password', 'password1', 'password2', 'codigo_hash'}


def registrar(usuario, accion, descripcion, objeto=None, cambios=None, modulo='', ip=None):
    usuario_valido = usuario if getattr(usuario, 'is_authenticated', False) else None
    try:
        # Savepoint propio: si esto falla, no arruina la transacción de quien llama
        with transaction.atomic():
            return RegistroActividad.objects.create(
                usuario=usuario_valido,
                usuario_texto=usuario_valido.get_username() if usuario_valido else '',
                accion=accion,
                modulo=modulo or (objeto._meta.app_label if objeto is not None else ''),
                descripcion=str(descripcion)[:300],
                objeto_tipo=objeto._meta.label if objeto is not None else '',
                objeto_id=str(objeto.pk) if objeto is not None and objeto.pk is not None else '',
                objeto_texto=str(objeto)[:200] if objeto is not None else '',
                cambios=cambios or {},
                ip=ip or ip_actual.get(),
            )
    except Exception:  # noqa: BLE001 — registrar nunca debe romper la operación
        logger.exception('No se pudo registrar la actividad: %s', descripcion)
        return None


def _texto(valor):
    if valor is None or valor == '':
        return ''
    if isinstance(valor, bool):
        return 'Sí' if valor else 'No'
    if hasattr(valor, 'strftime'):
        return valor.strftime('%d/%m/%Y')
    if hasattr(valor, 'name') and hasattr(valor, 'storage'):   # archivos
        return valor.name or ''
    return str(valor)


def cambios_de_formulario(form):
    """
    {campo: [antes, después]} con los campos que cambió un ModelForm ya
    validado, usando las etiquetas legibles ("Rol", no "rol_id").
    """
    cambios = {}
    for nombre in form.changed_data:
        campo = form.fields[nombre]
        etiqueta = str(campo.label or nombre)
        if nombre in CAMPOS_OCULTOS:
            cambios[etiqueta] = ['•••', '•••']
            continue
        antes = form.initial.get(nombre)
        despues = form.cleaned_data.get(nombre)
        # Para desplegables, mostrar el texto de la opción y no el valor guardado
        if hasattr(campo, 'queryset') and antes is not None:
            antes = campo.queryset.model._default_manager.filter(pk=antes).first()
        elif getattr(campo, 'choices', None) and not hasattr(campo, 'queryset'):
            opciones = {str(k): v for k, v in campo.choices}
            antes = opciones.get(str(antes), antes)
            despues = opciones.get(str(despues), despues)
        antes, despues = _texto(antes), _texto(despues)
        if antes != despues:
            cambios[etiqueta] = [antes, despues]
    return cambios
