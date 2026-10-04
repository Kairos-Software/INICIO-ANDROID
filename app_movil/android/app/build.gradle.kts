import java.io.FileInputStream
import java.util.Properties

plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

// La clave con la que se firma la APK de release. Los datos están en
// android/key.properties (NO va al repo; ver android/key.properties.ejemplo).
val propiedadesClave = Properties()
val archivoClave = rootProject.file("key.properties")
if (archivoClave.exists()) {
    propiedadesClave.load(FileInputStream(archivoClave))
}

android {
    namespace = "com.kairossoftware.app_movil"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    defaultConfig {
        // TODO: Specify your own unique Application ID (https://developer.android.com/studio/build/application-id.html).
        applicationId = "com.kairossoftware.app_movil"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        // Uses the version code from pubspec.yaml. When using split APKs, 1000 * ABI_VERSION
        // is added automatically by Flutter. (https://developer.android.com/studio/build/configure-apk-splits#configure-APK-versions)
        // You can force using the value of versionCode by specifying the `-P force-version-code-ignoring-abi=true`
        // flag during build.
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    signingConfigs {
        create("release") {
            if (archivoClave.exists()) {
                keyAlias = propiedadesClave["keyAlias"] as String
                keyPassword = propiedadesClave["keyPassword"] as String
                storeFile = file(propiedadesClave["storeFile"] as String)
                storePassword = propiedadesClave["storePassword"] as String
            }
        }
    }

    buildTypes {
        release {
            // Con key.properties: firma con TU clave. Sin él: con la clave de
            // prueba (sirve para probar, pero no para publicar ni actualizar).
            signingConfig = if (archivoClave.exists()) {
                signingConfigs.getByName("release")
            } else {
                signingConfigs.getByName("debug")
            }
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

flutter {
    source = "../.."
}
