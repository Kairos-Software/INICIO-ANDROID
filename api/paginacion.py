"""
Listados por páginas: ?pagina=2 (y opcional ?por_pagina=50, hasta 100).

    {"cantidad": 135, "pagina": 2, "paginas": 7,
     "siguiente": "http://.../?pagina=3", "anterior": "http://.../?pagina=1",
     "resultados": [...]}
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class Paginacion(PageNumberPagination):
    page_size = 20
    page_query_param = 'pagina'
    page_size_query_param = 'por_pagina'
    max_page_size = 100
    invalid_page_message = 'Esa página no existe.'

    def get_paginated_response(self, data):
        return Response({
            'cantidad': self.page.paginator.count,
            'pagina': self.page.number,
            'paginas': self.page.paginator.num_pages,
            'siguiente': self.get_next_link(),
            'anterior': self.get_previous_link(),
            'resultados': data,
        })


def paginar(request, queryset, serializer_class, **contexto):
    """Atajo para las vistas: pagina el queryset y devuelve la respuesta."""
    paginador = Paginacion()
    pagina = paginador.paginate_queryset(queryset, request)
    datos = serializer_class(pagina, many=True, context={'request': request, **contexto}).data
    return paginador.get_paginated_response(datos)
