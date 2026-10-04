"""
Los canales de TV para la app.

    GET /api/v1/canales/
      -> {"cantidad": 3,
          "categorias": [{"id": 1, "nombre": "Noticias",
                          "canales": [{"id", "nombre", "numero", "logo",
                                       "fuentes": [{"id", "url", "tipo"}, ...]}]}]}

Los ven los usuarios del panel y los clientes con el servicio vigente. Solo
van los canales que la app puede reproducir (fuentes HLS que no estén caídas).

    POST /api/v1/canales/fuentes/<id>/falla/
      -> {"estado": "funciona" | "caida" | "sin_verificar"}
      La app avisa que no pudo reproducir esa fuente. El servidor la vuelve a
      probar por su cuenta y, si también le falla, deja de mandarla.
"""

from rest_framework.decorators import api_view
from django.shortcuts import get_object_or_404
from rest_framework.response import Response

from canales.consultas import agrupar_por_categoria, canales_disponibles, fuentes_usables
from canales.servicios import reverificar_por_aviso
from canales.verificacion import verificar_url

from .serializers import CanalSerializer


@api_view(['GET'])
def lista(request):
    canales = list(canales_disponibles())
    contexto = {'request': request}
    return Response({
        'cantidad': len(canales),
        'categorias': [
            {
                'id': categoria.pk if categoria else None,
                'nombre': categoria.nombre if categoria else 'Otros',
                'canales': CanalSerializer(del_grupo, many=True, context=contexto).data,
            }
            for categoria, del_grupo in agrupar_por_categoria(canales)
        ],
    })


@api_view(['POST'])
def avisar_falla(request, pk):
    fuente = get_object_or_404(fuentes_usables().select_related('canal'), pk=pk)
    return Response({'estado': reverificar_por_aviso(fuente, verificar_url)})
