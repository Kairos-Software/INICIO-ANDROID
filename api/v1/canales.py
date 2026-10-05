"""
Los canales de TV para la app.

    GET /api/v1/canales/?formatos=hls,dash,directo,rtsp
      -> {"cantidad": 3,
          "categorias": [{"id": 1, "nombre": "Noticias",
                          "canales": [{"id", "nombre", "numero", "logo",
                                       "fuentes": [{"id", "url", "tipo", "user_agent", "referer"}, ...]}]}]}

Los ven los usuarios del panel y los clientes con el servicio vigente. Solo
van los canales que la app puede reproducir: `formatos` dice cuáles sabe
reproducir esa versión de la app (sin `formatos` = solo HLS, como la 1.0.0).

    GET /api/v1/canales/?contenido=pelicula   (o serie; sin nada = en vivo)

    GET /api/v1/canales/fuentes/<id>/resolver/
      -> {"url": "https://...m3u8", "tipo": "hls" | "dash" | "directo", "cabeceras": {...}}
      Para las fuentes "pagina" (Twitch, Dailymotion...): la dirección real
      del video en este momento (cambia seguido, por eso se pide al reproducir).
      YouTube no pasa por acá: lo resuelve la app en el aparato (ver canales/paginas.py).
      Si no se puede: 422 {"detalle": "El canal no está transmitiendo en vivo ahora."}

    POST /api/v1/canales/fuentes/<id>/falla/
      -> {"estado": "funciona" | "caida" | "sin_verificar"}
      La app avisa que no pudo reproducir esa fuente. El servidor la vuelve a
      probar por su cuenta y, si también le falla, deja de mandarla.
"""

from django.core.cache import cache
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from canales import paginas
from canales.consultas import agrupar_por_categoria, canales_disponibles, fuentes_usables, tipos_pedidos
from canales.models import Contenido, Fuente
from canales.servicios import reverificar_por_aviso
from canales.verificacion import verificar_url

from .serializers import CanalSerializer


@api_view(['GET'])
def lista(request):
    contenido = request.query_params.get('contenido')
    canales = list(canales_disponibles(tipos_pedidos(request.query_params.get('formatos')),
                                       contenido if contenido in Contenido.values else Contenido.VIVO))
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


# La dirección que entrega un sitio dura un rato: si varios aparatos piden la
# misma fuente casi a la vez, se reusa en vez de volver a consultar al sitio.
GUARDAR_RESUELTA = 90   # segundos


@api_view(['GET'])
def resolver(request, pk):
    fuente = get_object_or_404(fuentes_usables().filter(tipo=Fuente.Tipo.PAGINA), pk=pk)
    clave = f'fuente_resuelta:{fuente.pk}'
    datos = cache.get(clave)
    if datos is None:
        try:
            resuelto = paginas.resolver(fuente.url)
        except paginas.NoSePudo as error:
            return Response({'detalle': str(error)}, status=422)
        datos = {'url': resuelto.url, 'tipo': resuelto.tipo, 'cabeceras': resuelto.cabeceras}
        cache.set(clave, datos, GUARDAR_RESUELTA)
    return Response(datos)
