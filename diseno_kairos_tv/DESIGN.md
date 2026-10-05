# Kairos TV · sistema de diseño

## Principios

1. **TV en vivo primero.** Inicio abre con un canal destacado. Si hay favoritos, `Tus canales favoritos` es la primera fila.
2. **Legibilidad a tres metros.** En TV no se usa texto funcional menor de 14 px; títulos y acciones principales parten de 17 px.
3. **El foco es parte del diseño.** Nunca se depende solo del color: el elemento enfocado combina escala, borde, brillo y contraste.
4. **Datos honestos.** La interfaz funciona con nombre, número, logo, categoría, póster, temporada, episodio y progreso. EPG, sinopsis, puntajes, reparto y tráiler no forman parte del estado actual.
5. **Control remoto primero.** Toda acción de TV se alcanza con flechas, OK y Atrás. OK largo se reserva para favoritos sobre tarjetas.

## Colores

| Token | Valor | Uso |
|---|---:|---|
| Fondo | `#131317` | lienzo principal |
| Capa mínima | `#0E0E12` | barras, reproductor, fondos profundos |
| Capa baja | `#1B1B20` | modales y paneles |
| Capa | `#1F1F24` | tarjetas |
| Capa alta | `#2A292E` | controles y teclas |
| Capa máxima | `#353439` | divisores, progreso vacío |
| Borde suave | `#3B494B` | contornos inactivos |
| Texto | `#E4E1E8` | texto principal |
| Texto secundario | `#B9CACB` | descripciones |
| Texto apagado | `#849495` | ayudas y metadatos |
| Celeste | `#00F0FF` | foco, activo, CTA y progreso |
| Celeste claro | `#DBFCFF` | luces y texto sobre capas oscuras |
| Sobre celeste | `#002022` | texto sobre CTA celeste |
| Rubí | `#DF0041` | En vivo, favoritos y errores |
| Rubí claro | `#FFB3B5` | texto de error |
| Dorado | `#FFBA20` | números de canal y destacados |

El rubí no reemplaza al celeste para foco. Un favorito enfocado conserva el corazón rubí, pero recibe borde celeste.

## Tipografía

Plus Jakarta Sans se usa en títulos y nombres destacados. Inter se usa en navegación, botones, datos y textos.

### TV

| Uso | Familia / peso | Tamaño / interlínea |
|---|---|---:|
| Portada | Plus Jakarta Sans 800 | 50–64 / 1.06 |
| Título de pantalla | Plus Jakarta Sans 800 | 34 / 38 |
| Título de sección | Plus Jakarta Sans 800 | 28 / 34 |
| Título de tarjeta | Plus Jakarta Sans 700 | 20 / 26 |
| Botón | Inter 700 | 17 / 22 |
| Cuerpo | Inter 400 | 18 / 27 |
| Ayuda / metadato | Inter 400–700 | 14 / 20 |
| Insignia | Inter 800 | 12 / 16, tracking 0.08 em |

### Celular

| Uso | Familia / peso | Tamaño / interlínea |
|---|---|---:|
| Portada | Plus Jakarta Sans 800 | 30 / 38 |
| Título de pantalla | Plus Jakarta Sans 800 | 28 / 32 |
| Título de sección | Plus Jakarta Sans 700 | 20 / 28 |
| Cuerpo grande | Inter 400 | 16 / 24 |
| Cuerpo | Inter 400 | 14 / 20 |
| Etiqueta | Inter 600 | 12 / 16 |
| Barra inferior | Inter 700 | 10 / 14 |

## Espaciado y geometría

- Unidad base: `4 px`.
- Escala: `4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 96`.
- Margen seguro TV: `96 px` horizontal y `54 px` vertical (5 % del lienzo 1920×1080).
- Separación entre tarjetas TV: `20–22 px`; entre secciones: `26–32 px`.
- Margen celular: `16 px`.
- Radios: controles `12–14 px`, tarjetas `16–18 px`, paneles `20 px`, portada/modales `24 px`.
- Póster: proporción `2:3`.
- Canal: proporción `16:9`.
- Área mínima de foco TV: `58×58 px`.
- Área táctil mínima celular: `48×48 px`.

## Barras y vidrio

Las barras usan `#0E0E12` al 82–92 %, desenfoque de 20–24 px y borde `#3B494B` al 40–50 %. El contenido puede pasar por debajo, pero títulos y controles permanecen dentro de la zona segura.

## Foco TV

Estado obligatorio para cualquier elemento interactivo:

```css
transform: scale(1.055);          /* tarjetas; hasta 1.08 si hay espacio */
border: 3px solid #00F0FF;
box-shadow:
  0 0 0 3px rgba(219,252,255,.14),
  0 0 34px rgba(0,240,255,.48);
```

- Duración: `140 ms`; curva `ease-out`.
- El elemento enfocado vuelve a saturación y brillo completos.
- Los hermanos bajan a aproximadamente `80 %` de luminancia cuando ayuda a orientar.
- El foco no puede quedar cortado: las filas reservan 12 px extra arriba y abajo.
- Si una pantalla se restaura, vuelve al último foco válido. En el primer ingreso usa el foco inicial documentado abajo.

## Menú lateral TV

- Contraído: `88 px`, solo iconos.
- Se abre a `292 px` al presionar Izquierda desde la primera columna de contenido.
- Dentro del menú: Arriba/Abajo cambia de sección; Derecha vuelve al último foco del contenido; OK abre la sección.
- Orden: Inicio, En vivo, Guía, Películas, Series, Buscar, Favoritos y Mi cuenta al pie.
- El símbolo final del portal de cuatro paneles se usa en el menú. El logotipo horizontal queda reservado para acceso, banners y piezas de marca con espacio suficiente.

## Reglas del control remoto

- **OK corto:** abrir, reproducir, pausar o confirmar.
- **OK largo sobre tarjeta:** agregar/quitar favorito y mostrar confirmación breve.
- **Atrás:** cierra primero teclado, controles o modal; luego vuelve a la pantalla anterior.
- **Atrás en Inicio:** abre `¿Querés salir de Kairos TV?` con foco en `Seguir mirando`.
- **Números durante TV en vivo:** acumulan hasta 3 dígitos durante 1,5 s y cambian al canal coincidente.
- **Arriba/Abajo en reproducción en vivo:** zapping inmediato.
- **OK en reproducción en vivo:** muestra controles; si ya están visibles, abre la guía superpuesta.
- Los controles del reproductor se ocultan después de 5 s sin interacción.

## Recorrido por pantalla TV

| Pantalla | Foco inicial | Flechas | OK | Atrás |
|---|---|---|---|---|
| Login cliente | tecla `1` | recorre teclado; Arriba desde primera fila vuelve al campo | ingresa dígito; en `OK` valida | borra un dígito; vacío pregunta salir |
| Login panel | Usuario | Abajo a contraseña y botones; al editar abre teclado | edita o confirma | cierra teclado / vuelve a login cliente |
| Errores de login | acción del error activo | alterna acciones disponibles | reintenta o abre contacto | vuelve al código conservado |
| Inicio | `Ver en vivo` de portada | Derecha recorre acciones; Abajo entra a primera fila; Izquierda extrema abre menú | reproduce/abre | confirma salida |
| En vivo | primer canal de categoría activa | Izq/Der en fila; Arriba a filtros; Abajo a siguiente fila | reproduce canal | vuelve a Inicio |
| Guía sin EPG | primer canal | Arriba/Abajo cambia canal; Izquierda abre categorías/menú; Derecha acción secundaria | pantalla completa | pantalla anterior |
| Guía EPG futura | primer programa/canal | Arriba/Abajo canal; Izq/Der recorre programas y tiempos | reproduce desde vivo | guía anterior |
| Películas | primer póster | grilla geométrica; Arriba desde primera fila a filtros | detalle | pantalla anterior |
| Series | primer póster | igual a Películas | detalle | pantalla anterior |
| Detalle película | Reproducir | Derecha a Favorito; Abajo a similares | ejecuta acción | catálogo |
| Detalle serie | episodio en progreso | Arriba a temporada/acciones; Abajo entre episodios | reproduce episodio | catálogo |
| Reproductor vivo | botón Guía al mostrar controles | Izq/Der controles; Arriba/Abajo hace zapping con controles ocultos | guía superpuesta / acción | oculta controles o vuelve |
| Reproductor VOD | Pausa | Izq/Der controles; Abajo a línea de tiempo; en línea salta ±10 s | acción/pausa | oculta controles o vuelve |
| Buscar | campo de búsqueda | Abajo a resultados o teclado; teclado sigue geometría | escribe/abre resultado | cierra teclado; luego vuelve |
| Favoritos | primer canal | recorre filas separadas por tipo | reproduce/abre detalle; OK largo quita | pantalla anterior |
| Mi cuenta | `Volver al último canal` | Arriba/Abajo entre preferencias; Izquierda al perfil | alterna o abre | pantalla anterior |
| Servicio vencido | Contactar vendedor | Arriba/Abajo entre contacto y reintento | ejecuta acción | vuelve a login |
| Actualización | Actualizar | no cambia durante descarga; terminado pasa a Abrir | inicia/abre | permitido solo antes de iniciar |
| Error de señal | Probar de nuevo | Derecha a Guía | ejecuta acción | vuelve a guía |
| Confirmar salida | Seguir mirando | Izq/Der entre opciones | confirma | equivale a Seguir mirando |

## Guía sin programación

La versión principal no reserva columnas vacías para horarios. Cada fila usa solamente:

1. número de canal;
2. logo o iniciales;
3. nombre;
4. categoría;
5. indicación de OK.

Cuando el logo no existe, se muestran hasta tres iniciales sobre `#2A292E`, con texto `#DBFCFF`. Cuando el logo existe, se usa `contain`, nunca `cover`, dentro del mismo contenedor; así logos de medidas distintas no deforman la fila.

La EPG es una variante futura separada. Nunca deben mostrarse nombres u horarios inventados en producción.

## Favoritos y recientes

- Tipos separados: Canales, Películas, Series.
- Corazón rubí lleno = guardado; contorno = no guardado.
- En TV, OK largo sobre tarjeta alterna el estado. En detalle hay botón explícito.
- Si hay canales favoritos, su fila aparece inmediatamente bajo la portada de Inicio.
- Estado vacío: `Todavía no tenés favoritos` + explicación corta + botón `Explorar contenido`.
- `Últimos canales vistos` usa historial local y puede aparecer debajo de Favoritos.

## Reanudación y recuperación

- Si `Volver al último canal al abrir` está activo, mostrar una cuenta regresiva cancelable de 3 s antes de reproducir.
- Al fallar una fuente: `Este canal no está disponible. Probando otra señal…` y progreso indeterminado.
- Si todas fallan: acciones `Probar de nuevo` y `Volver a la guía`.
- No exponer URLs, protocolos ni detalles técnicos al cliente.

## Acceso y seguridad visual

- Código agrupado `4821 9037`; se muestran números durante la escritura porque la distancia de TV dificulta corregir, pero puede ocultarse tras 2 s en espacios públicos.
- El acceso de cliente es siempre el principal.
- Revendedores/administradores aparece como botón secundario, nunca como pestaña equivalente.
- Tras demasiados intentos, mostrar cuenta regresiva y bloquear la acción sin borrar el código.
- `Cuenta en uso` debe explicar el problema y ofrecer `Reintentar`; no prometer cierre remoto si esa función no existe.

## Celular

Se conserva el diseño Flutter aprobado. Los cambios son aditivos:

- Inicio prioriza canal en vivo y `Tus canales favoritos`.
- La barra inferior conserva las cinco secciones existentes y agrega `Favoritos` como sexto acceso. Las etiquetas bajan a 9 px, pero cada zona táctil conserva al menos 48 px de alto. `Mi Espacio` y el avatar superior siguen disponibles.
- La guía compacta mantiene filtros y búsqueda; no muestra programación.
- Login de cliente primero y acceso de panel como acción secundaria.

## Implementación Flutter

- TV: `FocusTraversalGroup` por región (menú, filtros, fila, modal) y `FocusNode` persistente por pantalla.
- Usar `Shortcuts`/`Actions` para OK largo, números y Atrás; no depender de `onTap`.
- Dar `semanticLabel` a logos, corazones y estados de señal.
- Respetar `MediaQuery.disableAnimations`; si está activo, eliminar escala y conservar borde/brillo.
- Las capturas muestran el foco inicial mediante una etiqueta de especificación. Esa etiqueta `FOCO INICIAL` no forma parte de la app final.
