import 'package:flutter/material.dart';

import '../sesion.dart';
import '../tema.dart';
import '../utiles.dart';
import '../widgets/comunes.dart';

/// "Mi cuenta" del cliente (entró con código): hasta cuándo puede ver,
/// cuántas pantallas tiene y cerrar sesión (libera su pantalla).
class PantallaCuentaCliente extends StatelessWidget {
  const PantallaCuentaCliente({super.key});

  Future<void> _salir(BuildContext context) async {
    final confirmar = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('¿Cerrar sesión?'),
        content: const Text('Esta pantalla queda libre. Para volver a entrar vas a necesitar tu código.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancelar')),
          TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('Cerrar sesión')),
        ],
      ),
    );
    if (confirmar == true && context.mounted) {
      await SesionScope.leer(context).salir();
    }
  }

  @override
  Widget build(BuildContext context) {
    final cliente = SesionScope.of(context).cliente;
    final dias = cliente?.diasRestantes;
    return Scaffold(
      appBar: AppBar(title: const Text('Mi cuenta')),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          Text(cliente?.nombre ?? '', style: estiloTitulo(26)),
          const SizedBox(height: 24),
          _Dato(icono: Icons.key_rounded, titulo: 'Tu código para entrar (anotalo)', valor: cliente?.codigo ?? '—'),
          _Dato(
            icono: Icons.event_available_rounded,
            titulo: 'Tu servicio vence',
            valor: cliente?.vence == null ? '—' : fechaLegible(cliente!.vence!.toIso8601String()),
            nota: dias == null ? null : (dias <= 3 ? '¡Quedan $dias día(s)! Renovalo con quien te lo vendió.' : null),
          ),
          _Dato(
            icono: Icons.tv_rounded,
            titulo: 'Pantallas',
            valor: '${cliente?.conectados ?? 0} en uso de ${cliente?.pantallas ?? 0}',
          ),
          const SizedBox(height: 32),
          OutlinedButton.icon(
            onPressed: () => _salir(context),
            icon: const Icon(Icons.logout_rounded),
            label: const Text('Cerrar sesión en este aparato'),
          ),
        ],
      ),
    );
  }
}

class _Dato extends StatelessWidget {
  const _Dato({required this.icono, required this.titulo, required this.valor, this.nota});

  final IconData icono;
  final String titulo;
  final String valor;
  final String? nota;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 18),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icono, color: Colores.celeste),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(titulo, style: const TextStyle(color: Colores.textoSuave, fontSize: 13)),
                Text(
                  valor,
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: Colores.texto),
                ),
                if (nota != null)
                  Text(
                    nota!,
                    style: const TextStyle(color: Colores.naranja, fontSize: 13, fontWeight: FontWeight.w600),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// El servicio del cliente venció o lo suspendieron. El token se conserva:
/// cuando renueve, "Ya renové" lo deja seguir sin volver a poner el código.
class PantallaSinServicio extends StatelessWidget {
  const PantallaSinServicio({super.key});

  @override
  Widget build(BuildContext context) {
    final sesion = SesionScope.of(context);
    return Scaffold(
      body: FondoMarca(
        child: SafeArea(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 460),
              child: Padding(
                padding: const EdgeInsets.all(28),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const MarcaKairos(tamanio: 64, vertical: true),
                    const SizedBox(height: 32),
                    const Icon(Icons.event_busy_rounded, size: 48, color: Colores.naranja),
                    const SizedBox(height: 16),
                    Text(
                      sesion.motivoSinServicio ?? 'Tu servicio no está activo.',
                      textAlign: TextAlign.center,
                      style: const TextStyle(fontSize: 18),
                    ),
                    const SizedBox(height: 28),
                    BotonDegradado(
                      texto: 'Ya renové, reintentar',
                      icono: Icons.refresh_rounded,
                      alTocar: sesion.reintentar,
                    ),
                    const SizedBox(height: 12),
                    TextButton(onPressed: sesion.salir, child: const Text('Entrar con otro código')),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
