import 'package:flutter/material.dart';

import '../api/modelos.dart';
import '../sesion.dart';
import '../tema.dart';
import '../utiles.dart';
import '../widgets/comunes.dart';
import 'reproductor.dart';

/// "TV en vivo": los canales agrupados por categoría (GET /api/v1/canales/).
class PantallaCanales extends StatefulWidget {
  const PantallaCanales({super.key});

  @override
  State<PantallaCanales> createState() => _PantallaCanalesState();
}

class _PantallaCanalesState extends State<PantallaCanales> {
  List<CategoriaCanales>? _categorias;
  Object? _error;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _cargar());
  }

  Future<void> _cargar() async {
    setState(() => _error = null);
    try {
      final datos = await SesionScope.leer(context).api.get('canales/') as Map<String, dynamic>;
      if (!mounted) return;
      setState(() => _categorias = [
            for (final c in datos['categorias'] as List) CategoriaCanales(c as Map<String, dynamic>),
          ]);
    } catch (error) {
      if (mounted) setState(() => _error = error);
    }
  }

  @override
  Widget build(BuildContext context) {
    final categorias = _categorias;
    return Scaffold(
      appBar: AppBar(
        title: const Row(
          children: [
            Icon(Icons.live_tv_rounded, color: Colores.celeste),
            SizedBox(width: 10),
            Text('TV en vivo'),
          ],
        ),
      ),
      body: _error != null && categorias == null
          ? VistaError(mensaje: textoDeError(_error!), alReintentar: _cargar)
          : categorias == null
              ? const Center(child: CircularProgressIndicator())
              : RefreshIndicator(
                  onRefresh: _cargar,
                  child: categorias.isEmpty
                      ? ListView(children: const [
                          SizedBox(height: 80),
                          VistaVacia(mensaje: 'Todavía no hay canales disponibles.', icono: Icons.tv_off_rounded),
                        ])
                      : ListView(
                          padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
                          children: [
                            for (final categoria in categorias) ...[
                              TituloSeccion(categoria.nombre),
                              GridView.builder(
                                shrinkWrap: true,
                                physics: const NeverScrollableScrollPhysics(),
                                gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                                  maxCrossAxisExtent: 140,
                                  mainAxisSpacing: 12,
                                  crossAxisSpacing: 12,
                                  childAspectRatio: 0.82,
                                ),
                                itemCount: categoria.canales.length,
                                itemBuilder: (context, i) => _TarjetaCanal(canal: categoria.canales[i]),
                              ),
                            ],
                          ],
                        ),
                ),
    );
  }
}

class _TarjetaCanal extends StatelessWidget {
  const _TarjetaCanal({required this.canal});

  final Canal canal;

  @override
  Widget build(BuildContext context) {
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => Navigator.push(
          context,
          MaterialPageRoute<void>(builder: (_) => PantallaReproductor(canal: canal)),
        ),
        child: Padding(
          padding: const EdgeInsets.all(10),
          child: Column(
            children: [
              Expanded(child: LogoCanal(canal: canal)),
              const SizedBox(height: 8),
              Text(
                canal.nombre,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13, color: Colores.texto),
              ),
              if (canal.numero.isNotEmpty)
                Text('Canal ${canal.numero}', style: const TextStyle(fontSize: 11, color: Colores.textoSuave)),
            ],
          ),
        ),
      ),
    );
  }
}

/// El logo del canal sobre un fondo claro (los logos vienen pensados para fondo blanco).
/// Si no tiene logo, o no carga, muestra las iniciales.
class LogoCanal extends StatelessWidget {
  const LogoCanal({super.key, required this.canal});

  final Canal canal;

  @override
  Widget build(BuildContext context) {
    final iniciales = canal.nombre.split(' ').where((p) => p.isNotEmpty).take(2).map((p) => p[0]).join().toUpperCase();
    final sinLogo = Center(
      child: Text(iniciales, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: Colores.fondo)),
    );
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(color: const Color(0xFFEFF3FF), borderRadius: BorderRadius.circular(Radios.chico)),
      child: canal.logo.isEmpty
          ? sinLogo
          : Image.network(canal.logo, fit: BoxFit.contain, errorBuilder: (_, _, _) => sinLogo),
    );
  }
}
