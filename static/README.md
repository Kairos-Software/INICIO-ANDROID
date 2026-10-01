# static/

Archivos estáticos generales: los que no cambian y se envían tal cual al
navegador.

## Subcarpetas

| Carpeta | Qué va |
|---|---|
| `css/` | Hojas de estilo generales del sistema |
| `js/` | JavaScript general del sistema |
| `img/` | Logos, íconos y otras imágenes generales |

## Qué NO va acá

- Estáticos propios de una sola app: van en `<app>/static/<app>/`.
- Archivos que suben los usuarios: van en `media/`.

## En producción

`python manage.py collectstatic` junta todos los estáticos (estos y los de
cada app) en la carpeta `staticfiles/`, que es la que sirve nginx. Esa carpeta
se genera sola y no va al repo.

## Archivos

| Archivo | Qué contiene |
|---|---|
| `css/sistema.css` | Estilos generales. Arriba de todo están los **TOKENS** (colores, tipografías, radios): para cambiar la marca de un proyecto alcanza con tocar ese bloque. |
| `js/sistema.js` | Comportamiento general: menú en celulares, mostrar/ocultar contraseña y el "momento" (hora en vivo, saludo y línea del día). |

Librerías externas (se cargan desde CDN en `templates/base_html.html`):
Bootstrap 5.3, Bootstrap Icons y las fuentes Bricolage Grotesque, Instrument
Sans y JetBrains Mono.

## Contenido actual

`sistema.css` y `sistema.js`. `img/` vacía (el `.gitkeep` solo sirve para
que git guarde la carpeta vacía).
