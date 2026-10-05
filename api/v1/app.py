"""
La última versión publicada de la app Android (la que se sube en el panel,
en "App Android"). La app la consulta al abrirse: si la suya es más vieja,
muestra el cartel "Hay una versión nueva" y la baja desde "descarga".

    GET /api/v1/app/   (sin sesión)
      -> 200 {"version": "1.1.0", "notas": "...", "descarga": "https://.../descargar/3/"}
      -> 200 {"version": null}   si todavía no se publicó ninguna

Es pública como /descargar/: también la consulta la pantalla de login.
"""

from django.urls import reverse
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from descargas.models import VersionApp


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def ultima_version(request):
    version = VersionApp.ultima()
    if version is None or not version.archivo:
        return Response({'version': None})
    return Response({
        'version': version.version,
        'notas': version.notas,
        # La de esa versión puntual (no /descargar/): si justo publican otra
        # mientras se baja, se instala la que se anunció.
        'descarga': request.build_absolute_uri(reverse('descargas:descargar_version', args=[version.pk])),
    })
