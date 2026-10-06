/// Funciones chicas que usan varias pantallas.
library;

import 'package:flutter/material.dart';

import 'api/cliente.dart';
import 'sesion.dart';
import 'tema.dart';

/// "2026-10-02" -> "02/10/2026". Vacío si no hay fecha.
String fechaLegible(Object? valor) {
  final texto = '${valor ?? ''}';
  if (texto.isEmpty || texto == 'null') return '';
  final fecha = DateTime.tryParse(texto);
  if (fecha == null) return texto;
  final local = fecha.isUtc ? fecha.toLocal() : fecha;
  final dia = '${local.day.toString().padLeft(2, '0')}/${local.month.toString().padLeft(2, '0')}/${local.year}';
  // Si traía hora (un "datetime"), también la muestra
  if (texto.contains('T')) {
    return '$dia ${local.hour.toString().padLeft(2, '0')}:${local.minute.toString().padLeft(2, '0')}';
  }
  return dia;
}

/// "Hace 5 minutos", "Hace 2 días"... (como el naturaltime de Django).
String haceCuanto(String fechaIso) {
  final fecha = DateTime.tryParse(fechaIso);
  if (fecha == null) return '';
  final diferencia = DateTime.now().difference(fecha.toLocal());
  if (diferencia.inMinutes < 1) return 'Recién';
  if (diferencia.inMinutes < 60) return 'Hace ${diferencia.inMinutes} min';
  if (diferencia.inHours < 24) return 'Hace ${diferencia.inHours} h';
  if (diferencia.inDays < 30) return 'Hace ${diferencia.inDays} ${diferencia.inDays == 1 ? 'día' : 'días'}';
  return fechaLegible(fechaIso);
}

String saludo() {
  final hora = DateTime.now().hour;
  if (hora < 6) return 'Buenas noches';
  if (hora < 13) return 'Buen día';
  if (hora < 20) return 'Buenas tardes';
  return 'Buenas noches';
}

/// Mensaje abajo de la pantalla (como los "messages" de Django).
void mostrarMensaje(BuildContext context, String texto, {bool error = false}) {
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(content: Text(texto), backgroundColor: error ? Colores.peligro : const Color(0xFF13806A)));
}

/// Texto de un error cualquiera, para mostrar.
String textoDeError(Object error) => error is ApiError ? error.detalle : 'Ocurrió un error inesperado.';

/// "¿Seguro?" con dos botones. Devuelve true si confirmó.
Future<bool> confirmar(
  BuildContext context, {
  required String titulo,
  required String mensaje,
  String aceptar = 'Aceptar',
  bool peligroso = false,
}) async {
  final respuesta = await showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      title: Text(titulo),
      content: Text(mensaje),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancelar')),
        TextButton(
          style: TextButton.styleFrom(foregroundColor: peligroso ? Colores.peligro : Colores.celeste),
          onPressed: () => Navigator.pop(context, true),
          child: Text(aceptar, style: const TextStyle(fontWeight: FontWeight.w700)),
        ),
      ],
    ),
  );
  return respuesta ?? false;
}

/// "¿Querés salir?" y, si confirma, cierra la sesión (el botón de salir de inicio y perfil).
Future<void> preguntarYSalir(BuildContext context) async {
  final salir = await confirmar(
    context,
    titulo: 'Cerrar sesión',
    mensaje: '¿Querés salir de la app en este celular?',
    aceptar: 'Salir',
    peligroso: true,
  );
  if (salir && context.mounted) await SesionScope.leer(context).salir();
}
