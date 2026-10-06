# reventa/

El **negocio de reventa** de Kairos TV: revendedores, sus clientes, los
créditos, los paquetes que se venden y las compras.

```
Revendedor 1 ──< Cliente 1 ──< Renovacion
     │              └──< Dispositivo   (cada pantalla conectada a la app)
     │
     ├──< Movimiento      (la libreta de créditos: + y −)
     └──< Compra >── Paquete
```

## Reglas del negocio

- **1 crédito = 1 dispositivo durante 30 días.**
- Un crédito comprado o regalado **no vence**: queda en el saldo hasta que
  se usa. Recién al usarse (activar o renovar a un cliente) dura 30 días.
- Al **activar o renovar** se elige cuántos dispositivos: N dispositivos =
  **N créditos**, siempre por 30 días. El cliente NO tiene un número fijo de
  dispositivos: es lo que pagó en el período en curso (se propone lo de la
  última vez).
- Renovar a un cliente vigente suma desde su vencimiento (no se pierden días).
- **No se pagan meses por adelantado:** si ya renovó el mes que viene, no se
  puede renovar otra vez hasta que ese mes empiece.
- **Créditos gratis:** el administrador se los regala a un revendedor.
- **Créditos pagos:** el administrador arma paquetes (créditos + precio). El
  revendedor pide uno y queda *pendiente*. Cuando el administrador confirma
  el pago, se suman los créditos. También puede cargar una compra ya pagada.
- El revendedor fija su **precio por dispositivo**. Al renovar se propone
  `precio × dispositivos`, pero se puede cambiar el monto realmente cobrado.
- **Ganancia del revendedor** = lo cobrado a sus clientes − lo pagado por sus créditos.
- **El revendedor también paga lo que mira:** con su usuario del panel NO ve
  los canales en la app (la API responde `revendedor_sin_pantalla`). En el
  inicio de reventa tiene **"Mi pantalla"**: un cliente propio
  (`Cliente.propio`, `servicios.pantalla_propia`) que activa con sus créditos
  como a cualquier otro, y entra a la app con ese código. El administrador
  (`administrar_reventa`) sí ve gratis con su usuario, para probar.
- **Clientes directos:** un cliente sin revendedor es de la empresa. Solo lo
  maneja el administrador y **no gasta créditos** (sirve también para probar).
  Lo que se le cobra cuenta como ingreso de la empresa.
- **Sesión única:** cada dispositivo pagado admite 1 aparato conectado. Si
  están todas ocupadas, el aparato nuevo se **bloquea** ("cuenta en uso").
  Un dispositivo sin señales durante 2 horas (`HORAS_SIN_SENAL`) se libera
  solo; el revendedor también puede liberarlo a mano desde la ficha del cliente.

## El saldo es una libreta

El saldo **no** es un número que se pisa: es la suma de los `Movimiento`
(+regalo, +compra, −renovación, ±ajuste). Así cada crédito tiene historia
(quién lo dio, cuándo y para qué), nada se pierde, y las estadísticas salen
solas. Todo lo que mueve créditos pasa por `servicios.py`, que bloquea la
fila del revendedor mientras trabaja: dos renovaciones al mismo tiempo no
pueden gastar el mismo crédito.

## Qué contiene

| Archivo | Capa | Para qué |
|---|---|---|
| `models.py` | Base | `Revendedor`, `Cliente` (con su código de acceso de 8 números), `Dispositivo`, `Renovacion`, `Paquete`, `Compra`, `Movimiento`. |
| `servicios.py` | Base | Crear revendedores y clientes, regalar / ajustar créditos, pedir / confirmar / cancelar compras, renovar, regenerar el código. |
| `consultas.py` | Base | Clientes visibles, filtros por estado, números de cada revendedor y del negocio. |
| `sesiones.py` | Base | La app de los clientes: entrar con el código, validar su token, la "señal", liberar inactivos. |
| `estadisticas.py` | Base | Mes a mes, ranking de revendedores, "ahora mismo" y los números de cada cliente. |
| `views.py`, `urls.py`, `forms.py`, `templates/` | Panel | Pantallas en `/reventa/`. |
| `admin.py` | Técnica | Vista técnica en `/admin/` (la libreta, compras y renovaciones son de solo lectura). |
| `tests/` | Técnica | Reglas del negocio y seguridad de las pantallas. |

## Quién ve qué

| Pantalla | Administrador (`administrar_reventa`) | Revendedor |
|---|---|---|
| `/reventa/` resumen | Números del negocio + compras pendientes | Sus números + clientes por vencer |
| `/reventa/clientes/` | Todos, también los directos (filtra por revendedor) | Solo los suyos |
| `/reventa/estadisticas/` | El negocio mes a mes + ranking de revendedores | Lo suyo mes a mes |
| `/reventa/creditos/` | — | Su saldo, comprar paquetes, su libreta |
| `/reventa/revendedores/` | Lista, alta, detalle, regalar / ajustar créditos | — |
| `/reventa/compras/` | Todas; confirmar pago (`confirmar_compras`) | Las suyas; cancelar las pendientes |
| `/reventa/paquetes/` | Con `gestionar_paquetes` | — |

Un revendedor **no necesita permisos**: entra porque tiene perfil de
`Revendedor`. El superusuario tiene todos los permisos. Los clientes siempre
se buscan dentro de los que el usuario puede ver: cambiar el número en la URL
da 404.

## El código de acceso del cliente

Cada cliente tiene un código fijo de 8 números (ej: `4821 9037`) para entrar
a la app. Es cómodo con el control remoto, y si cierra sesión o reinstala
vuelve a poner el mismo. Si se filtra, se genera otro desde su ficha (eso
desconecta todos sus dispositivos). Los códigos equivocados se cuentan por
conexión: tras varios intentos, se bloquea unos minutos (igual que el login
del panel). La API está en `api/v1/cliente.py`.

## Avisos (la campanita)

- Un revendedor pide un paquete → les llega a quienes confirman pagos.
- Se confirma el pago → le llega al revendedor.

## Pendiente

- Diseño nuevo del panel (con gráficos en las estadísticas).
- Pasarela de pago (hoy todo se confirma a mano).
