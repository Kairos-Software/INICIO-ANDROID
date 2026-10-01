"""
Catálogo de permisos del sistema y roles iniciales.

Es el ÚNICO lugar donde se declaran los permisos. Para sumar los de un
módulo nuevo (ej: clientes):

  1. Agregar un bloque en MODULOS_PERMISOS con sus códigos.
  2. Si alguno solo debe poder otorgarlo un superusuario, sumarlo a
     PERMISOS_RESTRINGIDOS.
  3. En las vistas del módulo, chequear con `chequear_permiso` o el
     decorador `requiere_permiso`.

No hace falta migración: los permisos se guardan como texto (código).
"""

# (nombre del módulo, [(código, descripción), ...])
# El orden de acá es el orden en que se muestran en las pantallas.
MODULOS_PERMISOS = [
    ('Usuarios', [
        ('ver_usuarios', 'Ver la lista y el detalle de los usuarios'),
        ('crear_usuarios', 'Crear usuarios'),
        ('editar_usuarios', 'Editar datos de usuarios y activarlos / desactivarlos'),
        ('restablecer_password_usuarios', 'Asignar una contraseña nueva a otro usuario'),
        ('eliminar_usuarios', 'Eliminar usuarios'),
        ('gestionar_permisos', 'Dar o quitar permisos individuales a otros usuarios'),
    ]),
    ('Roles', [
        ('ver_roles', 'Ver los roles y sus permisos'),
        ('crear_roles', 'Crear roles'),
        ('editar_roles', 'Editar roles existentes'),
        ('eliminar_roles', 'Eliminar roles'),
    ]),
    ('Sistema', [
        ('ver_actividad', 'Ver el registro de actividad (quién hizo qué y cuándo)'),
    ]),
]

PERMISOS_CHOICES = [
    permiso for _, permisos in MODULOS_PERMISOS for permiso in permisos
]
CODIGOS_PERMISOS = frozenset(codigo for codigo, _ in PERMISOS_CHOICES)
DESCRIPCION_PERMISO = dict(PERMISOS_CHOICES)

# Permisos que solo un superusuario puede otorgar (a un usuario o a un rol),
# aunque quien lo intente los tenga concedidos.
PERMISOS_RESTRINGIDOS = frozenset({
    'ver_roles',
    'crear_roles',
    'editar_roles',
    'eliminar_roles',
    'ver_actividad',
})


# Roles que crea `python manage.py crear_roles_iniciales`. Solo se crean si
# no existen: si después se editan desde el sistema, el comando no los pisa.
# '*' = todos los permisos del catálogo.
ROLES_INICIALES = [
    {
        'nombre': 'Administrador',
        'descripcion': 'Acceso completo: gestiona usuarios, permisos y roles.',
        'permisos': '*',
    },
    {
        'nombre': 'Supervisor',
        'descripcion': 'Gestiona usuarios del día a día, sin eliminar ni tocar permisos.',
        'permisos': [
            'ver_usuarios',
            'crear_usuarios',
            'editar_usuarios',
            'restablecer_password_usuarios',
        ],
    },
    {
        'nombre': 'Consulta',
        'descripcion': 'Solo puede ver información, sin modificar nada.',
        'permisos': [
            'ver_usuarios',
        ],
    },
    {
        'nombre': 'Operador',
        'descripcion': 'Usuario básico: entra al sistema y gestiona solo su propio perfil.',
        'permisos': [],
    },
]
