package com.kairossoftware.app_movil

import android.app.UiModeManager
import android.content.Context
import android.content.Intent
import android.content.res.Configuration
import android.net.Uri
import android.os.Build
import androidx.core.content.FileProvider
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.io.File

/**
 * Le pasa a Flutter datos del aparato que solo Android conoce:
 *   - nombre: fabricante y modelo (ej: "Philips 55PUD7406"). El servidor lo
 *     muestra en "Dispositivos conectados", para saber cuál liberar.
 *   - esTv: si corre en un televisor (Android TV / Google TV).
 *   - version: la versión de esta app instalada (la de pubspec.yaml).
 *   - carpetaTemporal: dónde dejar la APK nueva que se baja.
 * Y "instalar": abre el instalador de Android con esa APK (lib/actualizacion.dart);
 * "abrir": abre un enlace en otra app (ej: el WhatsApp del vendedor).
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
                        "version" to packageManager.getPackageInfo(packageName, 0).versionName,
                        "carpetaTemporal" to File(cacheDir, "actualizaciones").apply { mkdirs() }.absolutePath,
                    ))
                }
                "instalar" -> {
                    val archivo = File(llamada.argument<String>("ruta")!!)
                    // FileProvider: el instalador no puede leer la carpeta privada de la app,
                    // así que se le presta ese archivo con una dirección content://
                    val direccion = FileProvider.getUriForFile(this, "$packageName.archivos", archivo)
                    val instalar = Intent(Intent.ACTION_VIEW).apply {
                        setDataAndType(direccion, "application/vnd.android.package-archive")
                        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK)
                    }
                    try {
                        startActivity(instalar)
                        resultado.success(true)
                    } catch (e: Exception) {
                        resultado.error("sin_instalador", e.message, null)
                    }
                }
                "abrir" -> {
                    try {
                        startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(llamada.argument<String>("url")!!)))
                        resultado.success(true)
                    } catch (e: Exception) {
                        // Ninguna app lo sabe abrir (ej: una TV sin navegador ni WhatsApp)
                        resultado.success(false)
                    }
                }
                else -> resultado.notImplemented()
            }
        }
    }
}
