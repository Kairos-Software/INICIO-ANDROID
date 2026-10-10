# media/

Archivos que suben los usuarios desde el sistema: fotos de perfil, adjuntos,
documentos, etc.

## Importante

- Su contenido **no va al repo** (está en `.gitignore`, salvo este README).
- Cada entorno (PC, servidor) tiene sus propios archivos.
- En el servidor hay que incluirla en los backups junto con la base de datos.
- Django organiza las subcarpetas solo, según el `upload_to` de cada campo
  (por ejemplo `media/perfiles/`).

## Contenido actual

- `apk/`: las versiones de la app que se publican en /descargar/.
- `usuarios/fotos/`: fotos de perfil.
- `canales/imagenes/`: logos, pósters y portadas de series subidos desde
  Organizar contenido (la app los carga directo desde acá). Las que se
  reemplazan y ya nadie usa se borran solas.
