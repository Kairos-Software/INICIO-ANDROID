"""
Las notificaciones propias (cada uno ve solo las suyas).

    GET  /api/v1/notificaciones/                 ?no_leidas=1&pagina=   (incluye "no_leidas": cantidad)
    POST /api/v1/notificaciones/<id>/leida/      marcar una como leída
    POST /api/v1/notificaciones/marcar-todas/    marcar todas como leídas
"""

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from notificaciones import servicios

from ..paginacion import paginar
from .serializers import NotificacionSerializer


@api_view(['GET'])
def lista(request):
    notificaciones = request.user.notificaciones.all()
    if request.query_params.get('no_leidas') in ('1', 'true'):
        notificaciones = notificaciones.filter(leida_en__isnull=True)
    respuesta = paginar(request, notificaciones, NotificacionSerializer)
    respuesta.data['no_leidas'] = servicios.cantidad_no_leidas(request.user)
    return respuesta


@api_view(['POST'])
def marcar_leida(request, pk):
    notificacion = get_object_or_404(request.user.notificaciones, pk=pk)
    servicios.marcar_leida(notificacion)
    return Response(NotificacionSerializer(notificacion).data)


@api_view(['POST'])
def marcar_todas(request):
    return Response({'marcadas': servicios.marcar_todas_leidas(request.user)})
