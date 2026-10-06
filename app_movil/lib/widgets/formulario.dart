/// Arma formularios y vistas de datos a partir de las secciones de campos.
library;

import 'package:flutter/material.dart';

import '../api/cliente.dart';
import '../api/modelos.dart';
import '../campos.dart';
import '../utiles.dart';
import 'comunes.dart';

/// Filas "Etiqueta: valor" de un usuario, listas para [TarjetaDatos].
List<(String, String)> filasDeSeccion(Seccion seccion, Map<String, dynamic> datos) {
  return [for (final campo in seccion.campos) (campo.etiqueta, _valorLegible(campo, datos))];
}

String _valorLegible(Campo campo, Map<String, dynamic> datos) {
  final valor = datos[campo.nombre];
  switch (campo.tipo) {
    case TipoCampo.fecha:
      return fechaLegible(valor);
    case TipoCampo.opcion:
      return '${datos['${campo.nombre}_texto'] ?? ''}';
    case TipoCampo.rol:
      return '${datos['descripcion_rol'] ?? ''}';
    default:
      return valor == null ? '' : '$valor';
  }
}

/// Guarda lo que se va escribiendo en un formulario y sabe dibujar cada campo.
///
/// Es el equivalente a un Form de Django del lado de la app: tiene los
/// valores iniciales, los que cambia la persona, y muestra debajo de cada
/// campo el error que devolvió la API.
class DatosFormulario {
  DatosFormulario(List<Seccion> secciones, Map<String, dynamic> iniciales) {
    for (final seccion in secciones) {
      for (final campo in seccion.campos) {
        final valor = iniciales[campo.nombre];
        switch (campo.tipo) {
          case TipoCampo.opcion:
            elegidos[campo.nombre] = valor == null || valor == '' ? null : '$valor';
          case TipoCampo.rol:
            rol = (valor as Map?)?['id'] as int?;
          case TipoCampo.fecha:
            fechas[campo.nombre] = valor == null || valor == '' ? null : '$valor';
            textos[campo.nombre] = TextEditingController(text: fechaLegible(valor));
          default:
            textos[campo.nombre] = TextEditingController(text: valor == null ? '' : '$valor');
        }
      }
    }
  }

  final Map<String, TextEditingController> textos = {};
  final Map<String, String?> elegidos = {};
  final Map<String, String?> fechas = {};
  int? rol;

  /// Lo que se manda a la API: {"first_name": "Ana", "rol": 3, ...}.
  Map<String, dynamic> valores() {
    final resultado = <String, dynamic>{};
    textos.forEach((nombre, control) {
      if (!fechas.containsKey(nombre)) resultado[nombre] = control.text.trim();
    });
    elegidos.forEach((nombre, valor) => resultado[nombre] = valor ?? '');
    fechas.forEach((nombre, valor) => resultado[nombre] = valor ?? '');
    return resultado;
  }

  void liberar() {
    for (final control in textos.values) {
      control.dispose();
    }
  }
}

/// Dibuja todas las secciones de un formulario.
class CamposFormulario extends StatefulWidget {
  const CamposFormulario({
    super.key,
    required this.secciones,
    required this.datos,
    this.error,
    this.opciones = const {},
    this.roles = const [],
  });

  final List<Seccion> secciones;
  final DatosFormulario datos;
  final ApiError? error;

  /// Opciones de los campos de elegir: {"genero": [Opcion, ...]}.
  final Map<String, List<Opcion>> opciones;
  final List<RolOpcion> roles;

  @override
  State<CamposFormulario> createState() => _CamposFormularioState();
}

class _CamposFormularioState extends State<CamposFormulario> {
  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final seccion in widget.secciones) ...[
          TituloSeccion(seccion.titulo),
          for (final campo in seccion.campos) Padding(padding: const EdgeInsets.only(bottom: 12), child: _campo(campo)),
        ],
      ],
    );
  }

  Widget _campo(Campo campo) {
    final error = widget.error?.campo(campo.nombre);
    final decoracion = InputDecoration(labelText: campo.etiqueta, errorText: error, errorMaxLines: 3);

    switch (campo.tipo) {
      case TipoCampo.opcion:
        final opciones = widget.opciones[campo.nombre] ?? const <Opcion>[];
        final elegido = widget.datos.elegidos[campo.nombre];
        return DropdownButtonFormField<String?>(
          initialValue: opciones.any((o) => o.valor == elegido) ? elegido : null,
          decoration: decoracion,
          items: [
            const DropdownMenuItem(value: null, child: Text('—')),
            for (final opcion in opciones) DropdownMenuItem(value: opcion.valor, child: Text(opcion.texto)),
          ],
          onChanged: (valor) => widget.datos.elegidos[campo.nombre] = valor,
        );

      case TipoCampo.rol:
        final elegido = widget.datos.rol;
        return DropdownButtonFormField<int?>(
          initialValue: widget.roles.any((r) => r.id == elegido) ? elegido : null,
          isExpanded: true,
          decoration: decoracion.copyWith(
            helperText: 'Sin rol = permisos personalizados (se eligen desde la web).',
            helperMaxLines: 2,
          ),
          items: [
            const DropdownMenuItem(value: null, child: Text('Personalizado')),
            for (final rol in widget.roles)
              DropdownMenuItem(
                value: rol.id,
                // Un rol con permisos que vos no tenés no se puede elegir (igual que en la web)
                enabled: rol.puedeAsignar || rol.id == elegido,
                child: Text(
                  rol.puedeAsignar ? rol.nombre : '${rol.nombre} (no podés asignarlo)',
                  style: rol.puedeAsignar ? null : const TextStyle(color: Colors.grey),
                ),
              ),
          ],
          onChanged: (valor) => widget.datos.rol = valor,
        );

      case TipoCampo.fecha:
        return TextFormField(
          controller: widget.datos.textos[campo.nombre],
          readOnly: true,
          decoration: decoracion.copyWith(
            suffixIcon: widget.datos.fechas[campo.nombre] == null
                ? const Icon(Icons.calendar_today_outlined)
                : IconButton(
                    icon: const Icon(Icons.clear),
                    onPressed: () => setState(() {
                      widget.datos.fechas[campo.nombre] = null;
                      widget.datos.textos[campo.nombre]!.clear();
                    }),
                  ),
          ),
          onTap: () => _elegirFecha(campo),
        );

      default:
        return TextFormField(
          controller: widget.datos.textos[campo.nombre],
          decoration: decoracion,
          maxLines: campo.tipo == TipoCampo.multilinea ? 3 : 1,
          keyboardType: switch (campo.tipo) {
            TipoCampo.email => TextInputType.emailAddress,
            TipoCampo.telefono => TextInputType.phone,
            TipoCampo.numero => TextInputType.number,
            TipoCampo.multilinea => TextInputType.multiline,
            _ => TextInputType.text,
          },
          autocorrect: campo.tipo == TipoCampo.texto || campo.tipo == TipoCampo.multilinea,
        );
    }
  }

  Future<void> _elegirFecha(Campo campo) async {
    final actual = DateTime.tryParse(widget.datos.fechas[campo.nombre] ?? '');
    final elegida = await showDatePicker(
      context: context,
      initialDate: actual ?? DateTime(2000),
      firstDate: DateTime(1900),
      lastDate: DateTime(2100),
    );
    if (elegida == null) return;
    final iso = '${elegida.year}-${elegida.month.toString().padLeft(2, '0')}-${elegida.day.toString().padLeft(2, '0')}';
    setState(() {
      widget.datos.fechas[campo.nombre] = iso;
      widget.datos.textos[campo.nombre]!.text = fechaLegible(iso);
    });
  }
}
