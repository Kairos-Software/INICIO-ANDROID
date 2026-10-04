package com.kairossoftware.app_movil

import android.app.UiModeManager
import android.content.Context
import android.content.res.Configuration
import android.os.Build
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

/**
 * Le pasa a Flutter dos datos del aparato que solo Android conoce:
 *   - nombre: fabricante y modelo (ej: "Philips 55PUD7406"). El servidor lo
 *     muestra en "Dispositivos conectados", para saber cuál liberar.
 *   - esTv: si corre en un televisor (Android TV / Google TV).
 */
class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "kairos/dispositivo").setMethodCallHandler { llamada, resultado ->
            when (llamada.method) {
                "datos" -> {
                    val modos = getSystemService(Context.UI_MODE_SERVICE) as UiModeManager
                    val fabricante = Build.MANUFACTURER.replaceFirstChar { it.uppercase() }
                    val modelo = Build.MODEL
                    val nombre = if (modelo.startsWith(fabricante, ignoreCase = true)) modelo else "$fabricante $modelo"
                    resultado.success(mapOf(
                        "nombre" to nombre,
                        "esTv" to (modos.currentModeType == Configuration.UI_MODE_TYPE_TELEVISION),
                    ))
                }
                else -> resultado.notImplemented()
            }
        }
    }
}
