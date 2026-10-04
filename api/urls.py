from django.urls import include, path, re_path
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny


@api_view(['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
@authentication_classes([])
@permission_classes([AllowAny])
def no_existe(request, ruta=''):
    """Cualquier dirección inexistente bajo /api/ responde JSON (no la página 404 de la web)."""
    raise NotFound('Ese endpoint no existe.')


urlpatterns = [
    # Cada versión en su carpeta. Una v2 convivirá con la v1 sin romper las apps ya instaladas.
    path('v1/', include('api.v1.urls')),
    re_path(r'^(?P<ruta>.*)$', no_existe),
]
