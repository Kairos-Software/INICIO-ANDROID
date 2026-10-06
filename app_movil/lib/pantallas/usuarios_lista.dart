import 'package:flutter/material.dart';

import '../api/modelos.dart';
import '../sesion.dart';
import '../tema.dart';
import '../widgets/comunes.dart';
import '../widgets/lista_paginada.dart';
import 'usuario_detalle.dart';
import 'usuario_formulario.dart';

/// Lista de usuarios con búsqueda y filtro por estado (GET /api/v1/usuarios/).
class PantallaUsuarios extends StatefulWidget {
  const PantallaUsuarios({super.key});

  @override
  State<PantallaUsuarios> createState() => _PantallaUsuariosState();
}

class _PantallaUsuariosState extends State<PantallaUsuarios> {
  final _lista = GlobalKey<ListaPaginadaState<UsuarioResumen>>();
  final _busqueda = TextEditingController();
  String _estado = '';
  int? _cantidad;

  @override
  void dispose() {
    _busqueda.dispose();
    super.dispose();
  }

  Future<Pagina<UsuarioResumen>> _cargar(String? siguiente) async {
    final api = SesionScope.leer(context).api;
    final datos =
        await (siguiente != null
                ? api.get(siguiente)
                : api.get('usuarios/', parametros: {'q': _busqueda.text.trim(), 'estado': _estado}))
            as Map<String, dynamic>;
    return Pagina.desdeJson(datos, UsuarioResumen.new);
  }

  Future<void> _abrir(Widget pantalla) async {
    final cambio = await Navigator.push<bool>(context, MaterialPageRoute(builder: (_) => pantalla));
    if (cambio == true) _lista.currentState?.recargar();
  }

  @override
  Widget build(BuildContext context) {
    final perfil = SesionScope.of(context).perfil!;

    return Scaffold(
      appBar: AppBar(title: Text(_cantidad == null ? 'Usuarios' : 'Usuarios ($_cantidad)')),
      floatingActionButton: perfil.puede('crear_usuarios')
          ? FloatingActionButton.extended(
              onPressed: () => _abrir(const PantallaUsuarioFormulario()),
              icon: const Icon(Icons.person_add_alt_1),
              label: const Text('Nuevo'),
            )
          : null,
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
            child: TextField(
              controller: _busqueda,
              textInputAction: TextInputAction.search,
              decoration: InputDecoration(
                hintText: 'Buscar por nombre, usuario, email o documento',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: IconButton(
                  icon: const Icon(Icons.clear),
                  onPressed: () {
                    _busqueda.clear();
                    _lista.currentState?.recargar();
                  },
                ),
              ),
              onSubmitted: (_) => _lista.currentState?.recargar(),
            ),
          ),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
            child: Row(
              children: [
                for (final (valor, texto) in [('', 'Todos'), ('activos', 'Activos'), ('inactivos', 'Inactivos')])
                  Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: ChoiceChip(
                      label: Text(texto),
                      selected: _estado == valor,
                      onSelected: (_) {
                        setState(() => _estado = valor);
                        _lista.currentState?.recargar();
                      },
                    ),
                  ),
              ],
            ),
          ),
          Expanded(
            child: ListaPaginada<UsuarioResumen>(
              key: _lista,
              cargar: _cargar,
              mensajeVacio: 'No hay usuarios que coincidan.',
              alCargar: (pagina) => setState(() => _cantidad = pagina.cantidad),
              item: (context, usuario) => Card(
                child: ListTile(
                  onTap: () => _abrir(PantallaUsuarioDetalle(id: usuario.id)),
                  leading: Avatar(iniciales: usuario.iniciales, foto: usuario.foto),
                  title: Text(usuario.nombreCompleto, style: const TextStyle(fontWeight: FontWeight.w600)),
                  subtitle: Text('@${usuario.username} · ${usuario.descripcionRol}'),
                  trailing: usuario.activo ? null : const Etiqueta('Inactivo', color: Colores.peligro),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
