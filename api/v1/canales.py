"""
Los canales de TV para la app.

    GET /api/v1/canales/
      -> {"cantidad": 3,
          "categorias": [{"id": 1, "nombre": "Noticias",
                          "canales": [{"id", "nombre", "numero", "logo",
                                       "fuentes": [{"id", "url", "tipo"}, ...]}]}]}

Por ahora cualquier usuario con sesión los ve. Más adelante esto va a
depender del plan / los créditos del dispositivo.
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response

from canales.consultas import agrupar_por_categoria, canales_disponibles

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
