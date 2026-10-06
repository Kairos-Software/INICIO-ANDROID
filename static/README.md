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
| `css/sistema.css` | Base estructural histórica del panel: layout, componentes y compatibilidad de las pantallas existentes. Se carga primero. |
| `css/panel-kairos.css` | Capa visual final de Kairos TV. Contiene los tokens activos del tema oscuro y normaliza navegación, encabezados, tarjetas, métricas, filtros, tablas, formularios, estados vacíos, acceso y responsive. Se carga después de `sistema.css`. |
| `js/sistema.js` | Comportamiento general: menú en celulares, mostrar/ocultar contraseña, el "momento" (hora en vivo, saludo y línea del día) y las iniciales cuando el logo de un canal no carga. |
| `js/tandas.js` | Corre una tarea larga de a tandas (llama al servidor una y otra vez y pinta el avance). Lo usan las pantallas de canales para verificar listas grandes sin saturar el servidor. |

Librerías externas (se cargan desde CDN en `templates/base_html.html`):
Bootstrap 5.3, Bootstrap Icons y las fuentes Plus Jakarta Sans, Inter y
JetBrains Mono.

## Organización del CSS del panel

La responsabilidad está dividida en dos capas y el orden de carga es
importante:

1. `sistema.css` conserva la estructura y las clases que usan las plantillas.
2. `panel-kairos.css` aplica la identidad visual de Kairos TV y es la fuente de
   verdad para el aspecto final.

En `panel-kairos.css`, el bloque `:root` concentra la paleta, tipografías,
radios, espaciado, tamaños de controles, sombras y transiciones. Después se
ordenan los estilos por familia de componentes: controles, navegación,
superficies, datos, tablas y formularios, módulos específicos y acceso. La
sección **Auditoría visual integral** cierra la cascada con las reglas comunes
de densidad, accesibilidad y adaptación a celular que deben prevalecer sobre
la base histórica.

Para sumar una pantalla:

- reutilizá primero `pagina-encabezado`, `tarjeta`, `tarjeta-titulo`,
  `filtros`, `tabla`, `formulario-seccion`, `formulario-acciones`, `vacio` y
  los chips de estado;
- agregá una clase específica solo cuando la información necesite una
  composición propia;
- evitá colores, radios y separaciones nuevos dentro de la regla: agregá el
  token correspondiente en `:root`;
- mantené las tablas dentro de `table-responsive` y comprobá la pantalla a
  375 px;
- conservá un foco visible y un nombre accesible en controles que solo tengan
  ícono.

## Contenido actual

`sistema.css`, `panel-kairos.css`, `sistema.js`, `tandas.js` y los recursos de
marca dentro de `img/`.
