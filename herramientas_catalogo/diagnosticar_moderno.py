"""Filtra el catálogo moderno con el verificador real de KairosTV."""

import argparse
import json
import os
import sys
import zipfile
from collections import Counter
from pathlib import Path

PROYECTO = Path(__file__).resolve().parents[1]
RAIZ = PROYECTO.parent
sys.path.insert(0, str(PROYECTO))
sys.path.insert(0, str(RAIZ / "herramientas_catalogo"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "proyecto.settings")

import django

django.setup()

from canales import clasificar
from canales.m3u import leer_m3u
from canales.models import Importacion
from canales.servicios import juzgar
from canales.verificacion import verificar_varias
from generar_catalogos import Entry, m3u


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--a-fondo", action="store_true")
    args = parser.parse_args()

    salida = RAIZ / "catalogos-modernos"
    archivo = salida / "KairosTV_Moderno_Beta_Gratis.m3u"
    entradas = list(leer_m3u(archivo.read_text(encoding="utf-8-sig")))
    fuentes = {entrada.url: entrada.tipo for entrada in entradas}
    resultados = verificar_varias(fuentes, a_fondo=args.a_fondo)
    importacion = Importacion(solo_espanol=True, a_fondo=args.a_fondo)

    aptas: set[str] = set()
    motivos: Counter[str] = Counter()
    tipos: Counter[str] = Counter()
    for entrada in entradas:
        resultado = resultados.get(entrada.url)
        if resultado is None:
            motivos["sin_resultado"] += 1
            continue
        tipos[(resultado.estado, resultado.tipo, resultado.codec)] += 1
        causa, _ = juzgar(resultado, importacion)
        if resultado.estado == "funciona" and not causa:
            aptas.add(entrada.url)
        else:
            motivos[str(causa or resultado.estado)] += 1

    manifiesto = json.loads((salida / "manifest.json").read_text(encoding="utf-8"))
    seleccion = [Entry(**fila) for fila in manifiesto if fila["url"] in aptas]
    seleccion.sort(key=lambda e: (-(e.year or 0), e.group, e.title.lower()))
    destino = salida / "01_KairosTV_IMPORTAR_AHORA.m3u"
    destino.write_text(m3u(seleccion), encoding="utf-8-sig")

    instrucciones = salida / "INSTRUCCIONES_IMPORTACION.txt"
    instrucciones.write_text(
        "KAIROSTV - IMPORTACION DEL CATALOGO MODERNO\n"
        "============================================\n\n"
        "1. En Contenido, subi KairosTV_IMPORTAR_AHORA.zip.\n"
        "2. Deja DESMARCADA 'Prueba a fondo'. Esta lista ya fue comprobada con el verificador de KairosTV; "
        "la prueba profunda da falsos 'sin sonido' en varios MP4.\n"
        "3. Deja DESMARCADA 'Descartar peliculas y series'.\n"
        "4. Pulsa Empezar a probar y espera a que llegue a 100%.\n"
        "5. IMPORTANTE: pulsa 'Cargar las aptas'. Subir y probar no las carga automaticamente.\n\n"
        "La lista contiene solo las URLs que respondieron al verificador real de KairosTV en esta ejecucion.\n",
        encoding="utf-8",
    )
    paquete = salida / "KairosTV_IMPORTAR_AHORA.zip"
    with zipfile.ZipFile(paquete, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as comprimido:
        comprimido.write(destino, destino.name)
        comprimido.write(instrucciones, instrucciones.name)

    resumen = {
        "archivo_origen": archivo.name,
        "comprobadas_por_kairos": len(entradas),
        "incluidas_para_importar": len(seleccion),
        "prueba_a_fondo": args.a_fondo,
        "resultados_tecnicos": {str(k): v for k, v in tipos.items()},
        "excluidas": dict(motivos),
        "clasificacion": dict(Counter(
            clasificar.contenido(entrada.url, entrada.categoria) for entrada in entradas if entrada.url in aptas
        )),
    }
    (salida / "verificacion_kairos.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(resumen, ensure_ascii=False, indent=2))
    print(paquete)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
