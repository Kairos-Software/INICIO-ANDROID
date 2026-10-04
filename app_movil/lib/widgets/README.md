# lib/widgets/

Piezas de pantalla que se usan en varias pantallas (como
`templates/parciales/` en Django).

| Archivo | Qué tiene |
|---|---|
| `comunes.dart` | `MarcaKairos` (símbolo + nombre), `BotonDegradado` (botón principal), `IconoDegradado`, `Avatar` (foto o iniciales con aro en degradé), `VistaError` (con "Reintentar"), `VistaVacia`, `AvisoError`, `TituloSeccion`, `TarjetaDatos` (filas "etiqueta: valor"), `Etiqueta` (chip de color). |
| `barra_flotante.dart` | `BarraFlotante`: la navegación inferior flotante, con el ítem activo en degradé y contador de avisos. |
| `lista_paginada.dart` | `ListaPaginada`: lista que pide más páginas a la API al bajar (scroll infinito) y se recarga deslizando hacia abajo. |
| `formulario.dart` | `DatosFormulario` + `CamposFormulario`: arman un formulario a partir de las secciones de `campos.dart` y muestran debajo de cada campo el error que devolvió la API. `filasDeSeccion` arma las filas para ver los datos. |
