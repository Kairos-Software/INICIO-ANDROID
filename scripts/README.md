# scripts/

Scripts sueltos que no son parte del sistema en sí: tareas de mantenimiento,
migraciones de datos puntuales, utilidades de desarrollo o de despliegue.

## Qué va acá

- Scripts que se corren a mano y de vez en cuando (backup, importar datos
  viejos, preparar el servidor).

## Qué NO va acá

- Tareas que necesitan acceder a los modelos de Django de forma habitual:
  esas van como comando de la app que corresponde
  (`<app>/management/commands/`) y se corren con `python manage.py <comando>`.

## Contenido actual

Vacía por ahora.
