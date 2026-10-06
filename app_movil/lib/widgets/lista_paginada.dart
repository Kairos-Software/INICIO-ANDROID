/// Una lista que va pidiendo más páginas a la API a medida que bajás
/// (scroll infinito) y se recarga deslizando hacia abajo.
library;

import 'package:flutter/material.dart';

import '../api/modelos.dart';
import '../utiles.dart';
import 'comunes.dart';

class ListaPaginada<T> extends StatefulWidget {
  const ListaPaginada({
    super.key,
    required this.cargar,
    required this.item,
    this.mensajeVacio = 'No hay nada para mostrar.',
    this.alCargar,
  });

  /// Pide una página. `siguiente` es null para la primera.
  final Future<Pagina<T>> Function(String? siguiente) cargar;
  final Widget Function(BuildContext context, T item) item;
  final String mensajeVacio;

  /// Se llama con cada página que llega (ej: para actualizar un contador).
  final void Function(Pagina<T> pagina)? alCargar;

  @override
  State<ListaPaginada<T>> createState() => ListaPaginadaState<T>();
}

class ListaPaginadaState<T> extends State<ListaPaginada<T>> {
  final List<T> _items = [];
  final ScrollController _scroll = ScrollController();
  String? _siguiente;
  bool _cargando = false;
  bool _terminado = false;
  Object? _error;

  @override
  void initState() {
    super.initState();
    _scroll.addListener(() {
      if (_scroll.position.pixels > _scroll.position.maxScrollExtent - 300) {
        _cargarMas();
      }
    });
    recargar();
  }

  @override
  void dispose() {
    _scroll.dispose();
    super.dispose();
  }

  /// Vuelve a empezar desde la primera página (ej: después de crear o borrar algo).
  Future<void> recargar() async {
    setState(() {
      _items.clear();
      _siguiente = null;
      _terminado = false;
      _error = null;
    });
    await _cargarMas();
  }

  Future<void> _cargarMas() async {
    if (_cargando || _terminado) return;
    setState(() => _cargando = true);
    try {
      final pagina = await widget.cargar(_siguiente);
      if (!mounted) return;
      widget.alCargar?.call(pagina);
      setState(() {
        _items.addAll(pagina.resultados);
        _siguiente = pagina.siguiente;
        _terminado = pagina.siguiente == null;
      });
    } catch (error) {
      if (mounted) setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_error != null && _items.isEmpty) {
      return VistaError(mensaje: textoDeError(_error!), alReintentar: recargar);
    }
    if (_items.isEmpty && _cargando) {
      return const Center(child: CircularProgressIndicator());
    }
    return RefreshIndicator(
      onRefresh: recargar,
      child: _items.isEmpty
          ? ListView(
              children: [
                const SizedBox(height: 80),
                VistaVacia(mensaje: widget.mensajeVacio),
              ],
            )
          : ListView.separated(
              controller: _scroll,
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 96),
              itemCount: _items.length + (_terminado ? 0 : 1),
              separatorBuilder: (_, _) => const SizedBox(height: 8),
              itemBuilder: (context, indice) {
                if (indice >= _items.length) {
                  return const Padding(
                    padding: EdgeInsets.all(16),
                    child: Center(child: CircularProgressIndicator()),
                  );
                }
                return widget.item(context, _items[indice]);
              },
            ),
    );
  }
}
