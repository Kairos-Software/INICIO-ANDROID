"""
Usar los formularios de la web para validar lo que manda la app.

Así una regla (ej: "el email no se puede repetir") está escrita una sola
vez, en usuarios/forms.py, y vale igual para la web y para la API.

Los datos pueden llegar como JSON o como multipart (cuando la app sube una
foto). Los campos de la API se llaman igual que los del formulario web.
"""

from django.forms.models import model_to_dict
from django.http import QueryDict


def datos_planos(datos):
    """Un dict común con lo que mandó la app (sea JSON o multipart)."""
    if isinstance(datos, QueryDict):
        return datos.dict()
    return dict(datos) if hasattr(datos, 'keys') else {}


def datos_para_edicion(instancia, form_class, datos):
    """
    Para modificar (PATCH) la app manda SOLO lo que cambia. Un formulario de
    Django, en cambio, vaciaría lo que no viene. Por eso se completa con los
    valores actuales del objeto. La foto no: si no viene, queda la que está.
    """
    campos = [c for c in form_class._meta.fields if c != 'foto']
    return {**model_to_dict(instancia, fields=campos), **datos_planos(datos)}
