"""
Lo que el sistema HACE con la reventa (capa Base). Todo lo que mueve
créditos pasa por acá: las vistas solo llaman a estas funciones.

Cada operación que gasta o suma créditos bloquea la fila del revendedor
(select_for_update) mientras trabaja: así dos renovaciones al mismo tiempo
no pueden gastar el mismo crédito dos veces.

Los permisos (quién puede hacer qué) los chequean las vistas, no estas
funciones.
"""

from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from actividad.models import Accion
from actividad.registro import registrar
from notificaciones.models import Nivel
from notificaciones.servicios import notificar, notificar_a_quienes_puedan
from usuarios.models import Rol, Usuario

from .models import DIAS_POR_CREDITO, Cliente, Compra, Movimiento, Renovacion, Revendedor, _codigo_nuevo


NOMBRE_ROL = 'Revendedor'   # el mismo de usuarios/catalogo_permisos.py (ROLES_INICIALES)


class ReventaError(Exception):
    """Algo que no se puede hacer (sin saldo, compra ya resuelta...). El mensaje es para el usuario."""


def _bloquear(revendedor):
    return Revendedor.todos.select_for_update().get(pk=revendedor.pk)


# ── Revendedores ─────────────────────────────────────────────────────

def hacer_revendedor(usuario, precio_pantalla=0, por=None):
    """Convierte a un usuario del panel en revendedor (o devuelve el que ya era)."""
    revendedor, creado = Revendedor.todos.get_or_create(usuario=usuario, defaults={'precio_pantalla': precio_pantalla})
    if creado:
        registrar(por, Accion.CREAR, f'Hizo revendedor a {revendedor}', objeto=revendedor, modulo='reventa')
    elif revendedor.esta_eliminado:
        revendedor.restaurar(por)
    return revendedor


@transaction.atomic
def crear_revendedor(username, password, first_name='', last_name='', telefono='', precio_pantalla=0, por=None):
    """Alta completa: usuario del panel (con el rol Revendedor) + su perfil de revendedor."""
    rol, _ = Rol.objects.get_or_create(nombre=NOMBRE_ROL, defaults={
        'descripcion': 'Vende el servicio: gestiona sus clientes, sus créditos y sus compras.', 'permisos': []})
    usuario = Usuario.objects.create_user(
        username, None, password, first_name=first_name, last_name=last_name, telefono=telefono, rol=rol,
        debe_cambiar_password=True, creado_por=por if getattr(por, 'is_authenticated', False) else None,
    )
    return hacer_revendedor(usuario, precio_pantalla, por)


# ── Créditos ─────────────────────────────────────────────────────────

@transaction.atomic
def regalar_creditos(revendedor, cantidad, por=None, detalle=''):
    """Créditos gratis (los da el administrador)."""
    if cantidad <= 0:
        raise ReventaError('La cantidad tiene que ser mayor a 0.')
    _bloquear(revendedor)
    movimiento = Movimiento.objects.create(revendedor=revendedor, cantidad=cantidad, tipo=Movimiento.Tipo.REGALO,
                                           detalle=detalle[:200], hecho_por=por)
    registrar(por, Accion.CREAR, f'Regaló {cantidad} crédito(s) a {revendedor}', objeto=revendedor, modulo='reventa')
    return movimiento


@transaction.atomic
def ajustar_creditos(revendedor, cantidad, por=None, detalle=''):
    """Corrección del administrador (+ o −). El saldo nunca puede quedar negativo."""
    if cantidad == 0:
        raise ReventaError('La cantidad no puede ser 0.')
    if not detalle.strip():
        raise ReventaError('Explicá el motivo del ajuste.')
    revendedor = _bloquear(revendedor)
    if revendedor.saldo + cantidad < 0:
        raise ReventaError(f'El saldo quedaría negativo (tiene {revendedor.saldo}).')
    movimiento = Movimiento.objects.create(revendedor=revendedor, cantidad=cantidad, tipo=Movimiento.Tipo.AJUSTE,
                                           detalle=detalle[:200], hecho_por=por)
    registrar(por, Accion.EDITAR, f'Ajustó {cantidad:+d} crédito(s) a {revendedor}: {detalle}', objeto=revendedor,
              modulo='reventa')
    return movimiento


# ── Compras de paquetes ──────────────────────────────────────────────

def pedir_compra(revendedor, paquete, por=None):
    """El revendedor pide un paquete: queda pendiente hasta que se confirme el pago."""
    if not paquete.activo or paquete.esta_eliminado:
        raise ReventaError('Ese paquete ya no está disponible.')
    compra = Compra.objects.create(revendedor=revendedor, paquete=paquete, creditos=paquete.creditos,
                                   precio=paquete.precio, pedida_por=por)
    registrar(por, Accion.CREAR, f'Pidió el paquete "{paquete.nombre}" para {revendedor}', objeto=compra,
              modulo='reventa')
    # La campanita de quienes confirman pagos (no se avisa a sí mismo si la cargó el administrador)
    notificar_a_quienes_puedan('confirmar_compras', f'{revendedor} pidió {compra.creditos} créditos',
                               f'Paquete "{paquete.nombre}" por $ {compra.precio}. Confirmá el pago cuando lo recibas.',
                               url=reverse('reventa:compras'), nivel=Nivel.AVISO, excepto=por)
    return compra


@transaction.atomic
def confirmar_compra(compra, por=None):
    """Se cobró: la compra pasa a pagada y se suman los créditos."""
    compra = Compra.objects.select_for_update().get(pk=compra.pk)
    if compra.estado != Compra.Estado.PENDIENTE:
        raise ReventaError(f'La compra ya está {compra.get_estado_display().lower()}.')
    _bloquear(compra.revendedor)
    compra.estado, compra.resuelta, compra.resuelta_por = Compra.Estado.PAGADA, timezone.now(), por
    compra.save(update_fields=['estado', 'resuelta', 'resuelta_por'])
    Movimiento.objects.create(revendedor=compra.revendedor, cantidad=compra.creditos, tipo=Movimiento.Tipo.COMPRA,
                              detalle=f'Paquete "{compra.paquete.nombre if compra.paquete else "—"}"', compra=compra,
                              hecho_por=por)
    registrar(por, Accion.EDITAR, f'Confirmó el pago de {compra}', objeto=compra, modulo='reventa')
    notificar(compra.revendedor.usuario, f'Ya tenés tus {compra.creditos} créditos',
              'Se confirmó el pago de tu compra. Ya podés usarlos para activar y renovar clientes.',
              url=reverse('reventa:creditos'), nivel=Nivel.EXITO, excepto=por)
    return compra


@transaction.atomic
def cancelar_compra(compra, por=None):
    compra = Compra.objects.select_for_update().get(pk=compra.pk)
    if compra.estado != Compra.Estado.PENDIENTE:
        raise ReventaError(f'La compra ya está {compra.get_estado_display().lower()}.')
    compra.estado, compra.resuelta, compra.resuelta_por = Compra.Estado.CANCELADA, timezone.now(), por
    compra.save(update_fields=['estado', 'resuelta', 'resuelta_por'])
    registrar(por, Accion.EDITAR, f'Canceló la compra {compra}', objeto=compra, modulo='reventa')
    return compra


@transaction.atomic
def registrar_compra_pagada(revendedor, paquete, por=None):
    """El administrador carga una compra que ya cobró (sin pasar por 'pendiente')."""
    return confirmar_compra(pedir_compra(revendedor, paquete, por), por)


# ── Clientes ─────────────────────────────────────────────────────────

def crear_cliente(revendedor, nombre, telefono='', notas='', por=None):
    """
    Lo crea SIN activar: no gasta créditos. Cuántos dispositivos tiene se
    elige al activarlo (renovar).
    revendedor=None -> cliente directo de la empresa (solo para el administrador).
    """
    cliente = Cliente(revendedor=revendedor, nombre=nombre, telefono=telefono, notas=notas)
    cliente.marcar_autor(por)
    cliente.save()
    de_quien = f'de {revendedor}' if revendedor else '(directo)'
    registrar(por, Accion.CREAR, f'Creó el cliente {cliente} {de_quien}', objeto=cliente, modulo='reventa')
    return cliente


def precio_sugerido(cliente, dispositivos=1):
    precio = cliente.revendedor.precio_pantalla if cliente.revendedor_id else 0
    return precio * dispositivos


@transaction.atomic
def renovar(cliente, dispositivos=1, monto_cobrado=None, por=None):
    """
    Activa o renueva al cliente: `dispositivos` aparatos a la vez durante
    30 días. Gasta 1 crédito por dispositivo (un cliente directo no gasta).

    Si todavía está vigente, los 30 días nuevos empiezan cuando vence el
    actual (no se pierden días). Si estaba vencido, empiezan ahora. No se
    pagan meses por adelantado: si ya renovó el mes que viene, hay que
    esperar a que empiece.
    """
    if dispositivos < 1:
        raise ReventaError('Tiene que ser al menos 1 dispositivo.')
    cliente = Cliente.objects.select_for_update().get(pk=cliente.pk)
    if cliente.renovacion_adelantada():
        raise ReventaError(f'{cliente} ya tiene pagado el próximo mes (hasta el {cliente.vence:%d/%m/%Y}). '
                           'Se puede renovar de nuevo cuando empiece.')
    revendedor = _bloquear(cliente.revendedor) if cliente.revendedor_id else None
    creditos = dispositivos if revendedor else 0
    if revendedor and revendedor.saldo < creditos:
        raise ReventaError(f'No alcanzan los créditos: hacen falta {creditos} y quedan {revendedor.saldo}.')
    if monto_cobrado is None:
        monto_cobrado = precio_sugerido(cliente, dispositivos)
    if Decimal(monto_cobrado) < 0:
        raise ReventaError('El monto cobrado no puede ser negativo.')

    ahora = timezone.now()
    desde = cliente.vence if cliente.vence and cliente.vence > ahora else ahora
    hasta = desde + timedelta(days=DIAS_POR_CREDITO)
    renovacion = Renovacion.objects.create(cliente=cliente, pantallas=dispositivos, creditos=creditos,
                                           monto_cobrado=monto_cobrado, desde=desde, hasta=hasta, hecha_por=por)
    if revendedor:
        Movimiento.objects.create(revendedor=revendedor, cantidad=-creditos, tipo=Movimiento.Tipo.RENOVACION,
                                  detalle=f'{cliente.nombre}: {dispositivos} dispositivo(s)',
                                  renovacion=renovacion, hecho_por=por)
    cliente.vence = hasta
    cliente.marcar_autor(por)
    cliente.save(update_fields=['vence', 'modificado', 'modificado_por'])
    registrar(por, Accion.EDITAR, f'Renovó a {cliente} hasta el {hasta:%d/%m/%Y} ({creditos} crédito(s))',
              objeto=cliente, modulo='reventa')
    return renovacion


@transaction.atomic
def regenerar_codigo(cliente, por=None):
    """Código de acceso nuevo (si el anterior se filtró). Desconecta todos sus dispositivos."""
    cliente.codigo = _codigo_nuevo()
    cliente.marcar_autor(por)
    cliente.save(update_fields=['codigo', 'modificado', 'modificado_por'])
    cliente.dispositivos.all().delete()
    registrar(por, Accion.SEGURIDAD, f'Generó un código de acceso nuevo para {cliente}', objeto=cliente,
              modulo='reventa')
    return cliente


def liberar_dispositivos(cliente, dispositivo_id=None, por=None):
    """
    Desconecta un dispositivo (o todos): esa pantalla queda libre para otro
    aparato. El desconectado vuelve a la pantalla del código en la app.
    """
    dispositivos = cliente.dispositivos.all()
    if dispositivo_id is not None:
        dispositivos = dispositivos.filter(pk=dispositivo_id)
    cantidad, _ = dispositivos.delete()
    if cantidad:
        registrar(por, Accion.SEGURIDAD, f'Liberó {cantidad} dispositivo(s) de {cliente}', objeto=cliente,
                  modulo='reventa')
    return cantidad
