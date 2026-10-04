"""
Pantallas de reventa del panel.

Dos tipos de acceso:
  - administrador (permiso `administrar_reventa`; el superusuario lo tiene):
    ve y opera sobre TODOS los revendedores y clientes.
  - revendedor (tiene perfil de Revendedor): ve y opera SOLO lo suyo.

Nunca se confía en lo que viene en la URL: los clientes se buscan siempre
dentro de los que el usuario puede ver (`_clientes_visibles`), así un
revendedor no puede abrir el cliente de otro cambiando el número.

Las reglas del negocio (saldo, renovar, confirmar pagos) están en servicios.py.
"""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from usuarios.decoradores import requiere_permiso
from usuarios.permisos import chequear_permiso

from . import consultas, estadisticas, servicios
from .forms import (ClienteForm, CreditosForm, ElegirPaqueteForm, PaqueteForm, PrecioForm, RenovarForm,
                    RevendedorNuevoForm)
from .models import HORAS_SIN_SENAL, Compra, Paquete, Revendedor
from .servicios import ReventaError

POR_PAGINA = 25


def requiere_reventa(vista):
    """Deja pasar al administrador de reventa o a un revendedor. Completa request.revendedor / request.es_admin."""
    @wraps(vista)
    def envoltorio(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        request.es_admin = chequear_permiso(request.user, 'administrar_reventa')
        request.revendedor = Revendedor.objects.filter(usuario=request.user).first()
        if not request.es_admin and request.revendedor is None:
            raise PermissionDenied
        return vista(request, *args, **kwargs)
    return envoltorio


def _clientes_visibles(request):
    return consultas.clientes_de(None if request.es_admin else request.revendedor)


def _ejecutar(request, funcion, *args, exito='', **kwargs):
    """Llama a un servicio y convierte su resultado o su ReventaError en un mensaje."""
    try:
        resultado = funcion(*args, por=request.user, **kwargs)
    except ReventaError as error:
        messages.error(request, str(error))
        return None
    if exito:
        messages.success(request, exito)
    return resultado


# ── Inicio ───────────────────────────────────────────────────────────

@requiere_reventa
def inicio(request):
    contexto = {}
    if request.es_admin:
        contexto['general'] = consultas.resumen_general()
        contexto['pendientes'] = Compra.objects.filter(estado=Compra.Estado.PENDIENTE).select_related(
            'revendedor__usuario')[:10]
    if request.revendedor:
        contexto['mio'] = consultas.resumen_revendedor(request.revendedor)
        contexto['por_vencer'] = consultas.filtrar_clientes(
            consultas.clientes_de(request.revendedor), 'por_vencer').order_by('vence')[:10]
    return render(request, 'reventa/inicio.html', contexto)


@requiere_reventa
def ver_estadisticas(request):
    """El administrador ve el negocio entero (y el ranking); el revendedor, lo suyo."""
    revendedor = None if request.es_admin else request.revendedor
    filas = estadisticas.por_mes(revendedor)
    return render(request, 'reventa/estadisticas.html', {
        'es_negocio': revendedor is None,
        'filas': filas,
        'total': estadisticas.totales(filas),
        'en_vivo': estadisticas.en_vivo(revendedor),
        'ranking': estadisticas.ranking_revendedores() if revendedor is None else None,
    })


# ── Revendedores (administrador) ─────────────────────────────────────

@requiere_permiso('administrar_reventa')
def revendedores(request):
    texto = request.GET.get('q', '').strip()
    lista = consultas.revendedores_con_numeros()
    if texto:
        lista = lista.filter(usuario__username__icontains=texto) | lista.filter(usuario__first_name__icontains=texto) \
            | lista.filter(usuario__last_name__icontains=texto)
    return render(request, 'reventa/revendedores.html', {'revendedores': lista, 'texto': texto})


@requiere_permiso('administrar_reventa')
def revendedor_nuevo(request):
    form = RevendedorNuevoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        revendedor = servicios.crear_revendedor(por=request.user, **form.cleaned_data)
        messages.success(request, f'Se creó el revendedor {revendedor}. Pasale su usuario y contraseña.')
        return redirect('reventa:revendedor', pk=revendedor.pk)
    return render(request, 'reventa/formulario.html', {
        'form': form, 'titulo': 'Nuevo revendedor', 'volver': reverse('reventa:revendedores'),
        'bajada': 'Se crea su usuario para entrar al panel, con el rol Revendedor.',
    })


@requiere_permiso('administrar_reventa')
def revendedor(request, pk):
    revendedor = get_object_or_404(Revendedor.objects.select_related('usuario'), pk=pk)
    movimientos = Paginator(revendedor.movimientos.select_related('hecho_por'), POR_PAGINA).get_page(
        request.GET.get('pagina'))
    return render(request, 'reventa/revendedor.html', {
        'revendedor': revendedor,
        'numeros': consultas.resumen_revendedor(revendedor),
        'movimientos': movimientos,
        'clientes': consultas.clientes_de(revendedor).order_by('vence')[:50],
        'compras': revendedor.compras.select_related('paquete')[:20],
        'form_creditos': CreditosForm(),
        'form_precio': PrecioForm(instance=revendedor),
        'form_paquete': ElegirPaqueteForm(),
        'puede_confirmar': chequear_permiso(request.user, 'confirmar_compras'),
    })


@require_POST
@requiere_permiso('administrar_reventa')
def revendedor_accion(request, pk):
    """Regalar / ajustar créditos, cambiar el precio o cargar una compra ya pagada."""
    revendedor = get_object_or_404(Revendedor, pk=pk)
    accion = request.POST.get('accion')
    if accion in ('regalar', 'ajustar'):
        form = CreditosForm(request.POST)
        if form.is_valid():
            datos = form.cleaned_data
            if accion == 'regalar':
                _ejecutar(request, servicios.regalar_creditos, revendedor, datos['cantidad'], detalle=datos['detalle'],
                          exito=f'Se regalaron {datos["cantidad"]} crédito(s).')
            else:
                _ejecutar(request, servicios.ajustar_creditos, revendedor, datos['cantidad'], detalle=datos['detalle'],
                          exito=f'Se ajustaron {datos["cantidad"]:+d} crédito(s).')
        else:
            messages.error(request, 'Revisá la cantidad.')
    elif accion == 'precio':
        form = PrecioForm(request.POST, instance=revendedor)
        if form.is_valid():
            revendedor.marcar_autor(request.user)
            form.save()
            messages.success(request, 'Precio actualizado.')
    elif accion == 'compra':
        if not chequear_permiso(request.user, 'confirmar_compras'):
            raise PermissionDenied
        form = ElegirPaqueteForm(request.POST)
        if form.is_valid():
            _ejecutar(request, servicios.registrar_compra_pagada, revendedor, form.cleaned_data['paquete'],
                      exito='Compra cargada como pagada: los créditos ya están en su saldo.')
    return redirect('reventa:revendedor', pk=pk)


# ── Clientes ─────────────────────────────────────────────────────────

@requiere_reventa
def clientes(request):
    filtros = {'texto': request.GET.get('q', '').strip(), 'estado': request.GET.get('estado', ''),
               'revendedor': request.GET.get('revendedor', '') if request.es_admin else ''}
    lista = consultas.filtrar_clientes(_clientes_visibles(request), filtros['estado'])
    if filtros['texto']:
        lista = lista.filter(nombre__icontains=filtros['texto']) | lista.filter(telefono__icontains=filtros['texto']) \
            | lista.filter(codigo=filtros['texto'].replace(' ', ''))
    if filtros['revendedor'] == 'directos':
        lista = lista.filter(revendedor__isnull=True)
    elif filtros['revendedor'].isdigit():
        lista = lista.filter(revendedor_id=filtros['revendedor'])
    parametros = request.GET.copy()
    parametros.pop('pagina', None)
    return render(request, 'reventa/clientes.html', {
        'pagina': Paginator(lista.order_by('nombre'), POR_PAGINA).get_page(request.GET.get('pagina')),
        'filtros': filtros,
        'hay_filtros': any(filtros.values()),
        'revendedores': Revendedor.objects.select_related('usuario') if request.es_admin else None,
        'parametros': parametros.urlencode(),
    })


@requiere_reventa
def cliente_nuevo(request):
    # El administrador elige de qué revendedor es (o lo deja directo, sin revendedor)
    elegir = request.es_admin
    form = ClienteForm(request.POST or None, elegir_revendedor=elegir,
                       initial={'revendedor': request.revendedor} if elegir else None)
    if request.method == 'POST' and form.is_valid():
        datos = form.cleaned_data
        cliente = servicios.crear_cliente(
            datos['revendedor'] if elegir else request.revendedor, datos['nombre'], telefono=datos['telefono'],
            notas=datos['notas'], por=request.user)
        messages.success(request, f'Se creó el cliente {cliente}. Para que pueda ver, activalo.')
        return redirect('reventa:cliente', pk=cliente.pk)
    return render(request, 'reventa/formulario.html', {
        'form': form, 'titulo': 'Nuevo cliente', 'volver': reverse('reventa:clientes'),
        'bajada': 'Crearlo no gasta créditos: se gastan recién al activarlo.',
    })


@requiere_reventa
def cliente(request, pk):
    cliente = get_object_or_404(_clientes_visibles(request), pk=pk)
    return render(request, 'reventa/cliente.html', {
        'cliente': cliente,
        'renovaciones': cliente.renovaciones.select_related('hecha_por')[:30],
        'form_renovar': RenovarForm(initial={'dispositivos': cliente.ultimos_dispositivos()}),
        'precio_dispositivo': servicios.precio_sugerido(cliente),
        'adelantada': cliente.renovacion_adelantada(),
        'saldo': cliente.revendedor.saldo if cliente.revendedor_id else None,
        'dispositivos': cliente.dispositivos.all(),
        'numeros': estadisticas.numeros_cliente(cliente),
        'horas_sin_senal': HORAS_SIN_SENAL,
    })


@requiere_reventa
def cliente_editar(request, pk):
    cliente = get_object_or_404(_clientes_visibles(request), pk=pk)
    form = ClienteForm(request.POST or None, instance=cliente)
    if request.method == 'POST' and form.is_valid():
        cliente.marcar_autor(request.user)
        form.save()
        messages.success(request, 'Cliente actualizado.')
        return redirect('reventa:cliente', pk=pk)
    return render(request, 'reventa/formulario.html', {
        'form': form, 'titulo': f'Editar {cliente}', 'volver': reverse('reventa:cliente', args=[cliente.pk]),
    })


@require_POST
@requiere_reventa
def cliente_renovar(request, pk):
    cliente = get_object_or_404(_clientes_visibles(request), pk=pk)
    form = RenovarForm(request.POST)
    if form.is_valid():
        renovacion = _ejecutar(request, servicios.renovar, cliente, form.cleaned_data['dispositivos'],
                               monto_cobrado=form.cleaned_data['monto_cobrado'])
        if renovacion:
            messages.success(request, f'Listo: {cliente} puede ver hasta el {renovacion.hasta:%d/%m/%Y} '
                                      f'con {renovacion.pantallas} dispositivo(s) ({renovacion.creditos} crédito(s) usados).')
    else:
        messages.error(request, 'Revisá los dispositivos y el monto.')
    return redirect('reventa:cliente', pk=pk)


@require_POST
@requiere_reventa
def cliente_liberar(request, pk):
    """Desconecta un dispositivo (o todos, si no viene cuál): su pantalla queda libre."""
    cliente = get_object_or_404(_clientes_visibles(request), pk=pk)
    dispositivo = request.POST.get('dispositivo', '')
    cantidad = servicios.liberar_dispositivos(cliente, int(dispositivo) if dispositivo.isdigit() else None,
                                              por=request.user)
    messages.success(request, f'Se liberaron {cantidad} dispositivo(s).' if cantidad else 'No había nada para liberar.')
    return redirect('reventa:cliente', pk=pk)


@require_POST
@requiere_reventa
def cliente_codigo(request, pk):
    cliente = get_object_or_404(_clientes_visibles(request), pk=pk)
    _ejecutar(request, servicios.regenerar_codigo, cliente, exito='Se generó un código nuevo. El anterior ya no sirve.')
    return redirect('reventa:cliente', pk=pk)


# ── Créditos y compras del revendedor ────────────────────────────────

@requiere_reventa
def creditos(request):
    """La libreta y las compras del revendedor que está mirando."""
    if request.revendedor is None:
        return redirect('reventa:revendedores')   # el administrador ve los de cada uno
    revendedor = request.revendedor
    return render(request, 'reventa/creditos.html', {
        'numeros': consultas.resumen_revendedor(revendedor),
        'movimientos': Paginator(revendedor.movimientos.all(), POR_PAGINA).get_page(request.GET.get('pagina')),
        'compras': revendedor.compras.select_related('paquete')[:20],
        'paquetes': Paquete.objects.filter(activo=True),
    })


@require_POST
@requiere_reventa
def pedir_compra(request):
    if request.revendedor is None:
        raise PermissionDenied
    paquete = get_object_or_404(Paquete, pk=request.POST.get('paquete'))
    _ejecutar(request, servicios.pedir_compra, request.revendedor, paquete,
              exito='Compra pedida. Los créditos se suman cuando se confirme el pago.')
    return redirect('reventa:creditos')


# ── Paquetes (superusuario / gestionar_paquetes) ─────────────────────

@requiere_permiso('gestionar_paquetes')
def paquetes(request):
    return render(request, 'reventa/paquetes.html', {'paquetes': Paquete.objects.all()})


@requiere_permiso('gestionar_paquetes')
def paquete_editar(request, pk=None):
    paquete = get_object_or_404(Paquete, pk=pk) if pk else None
    form = PaqueteForm(request.POST or None, instance=paquete)
    if request.method == 'POST' and form.is_valid():
        nuevo = form.save(commit=False)
        nuevo.marcar_autor(request.user)
        nuevo.save()
        messages.success(request, f'Paquete "{nuevo.nombre}" guardado.')
        return redirect('reventa:paquetes')
    return render(request, 'reventa/formulario.html', {
        'form': form, 'titulo': f'Editar "{paquete.nombre}"' if paquete else 'Nuevo paquete',
        'volver': reverse('reventa:paquetes'),
        'bajada': 'Cambiar el precio no afecta a las compras ya hechas.',
    })


# ── Compras (confirmar pagos) ────────────────────────────────────────

@requiere_reventa
def compras(request):
    """El administrador ve todas; el revendedor, las suyas."""
    estado = request.GET.get('estado', Compra.Estado.PENDIENTE if request.es_admin else '')
    lista = Compra.objects.select_related('revendedor__usuario', 'paquete')
    if not request.es_admin:
        lista = lista.filter(revendedor=request.revendedor)
    if estado:
        lista = lista.filter(estado=estado)
    return render(request, 'reventa/compras.html', {
        'pagina': Paginator(lista, POR_PAGINA).get_page(request.GET.get('pagina')),
        'estado': estado,
        'estados': Compra.Estado.choices,
        'puede_confirmar': chequear_permiso(request.user, 'confirmar_compras'),
    })


@require_POST
@requiere_reventa
def compra_resolver(request, pk):
    """Confirmar (solo quien confirma pagos) o cancelar (también el revendedor, la suya pendiente)."""
    compra = get_object_or_404(Compra, pk=pk)
    puede_confirmar = chequear_permiso(request.user, 'confirmar_compras')
    es_suya = request.revendedor is not None and compra.revendedor_id == request.revendedor.pk
    accion = request.POST.get('accion')
    if accion == 'confirmar' and puede_confirmar:
        _ejecutar(request, servicios.confirmar_compra, compra, exito=f'Pago confirmado: +{compra.creditos} créditos.')
    elif accion == 'cancelar' and (puede_confirmar or es_suya):
        _ejecutar(request, servicios.cancelar_compra, compra, exito='Compra cancelada.')
    else:
        raise PermissionDenied
    # Solo a lugares conocidos (nunca a una dirección que venga en el formulario)
    if request.POST.get('volver') == 'revendedor':
        return redirect('reventa:revendedor', pk=compra.revendedor_id)
    return redirect('reventa:inicio' if request.POST.get('volver') == 'inicio' else 'reventa:compras')
