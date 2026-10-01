/* sistema.js — comportamiento general del sistema (sin dependencias) */

(function () {
    'use strict';

    // ── Menú lateral en celulares ──────────────────────────────────
    const app = document.querySelector('.app');
    document.querySelectorAll('[data-accion="abrir-menu"]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            app.classList.add('menu-abierto');
            btn.setAttribute('aria-expanded', 'true');
        });
    });
    document.querySelectorAll('[data-accion="cerrar-menu"]').forEach(function (el) {
        el.addEventListener('click', function () { app.classList.remove('menu-abierto'); });
    });
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && app) app.classList.remove('menu-abierto');
    });

    // ── Mostrar / ocultar contraseña ───────────────────────────────
    document.querySelectorAll('[data-accion="ver-password"]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            const input = document.getElementById(btn.dataset.objetivo);
            const visible = input.type === 'text';
            input.type = visible ? 'password' : 'text';
            btn.setAttribute('aria-label', visible ? 'Mostrar contraseña' : 'Ocultar contraseña');
            btn.querySelector('i').className = visible ? 'bi bi-eye' : 'bi bi-eye-slash';
        });
    });

    // ── Marcar / desmarcar todos los checkboxes de un grupo ────────
    // <button data-accion="marcar-grupo" data-grupo="id-del-contenedor">
    // Solo toca los que no están bloqueados. Si ya están todos marcados, los desmarca.
    document.querySelectorAll('[data-accion="marcar-grupo"]').forEach(function (btn) {
        const grupo = document.getElementById(btn.dataset.grupo);
        const casillas = function () {
            return Array.from(grupo.querySelectorAll('input[type="checkbox"]:not(:disabled)'));
        };
        const actualizarTexto = function () {
            const todas = casillas();
            btn.hidden = todas.length === 0;
            btn.textContent = todas.length && todas.every(function (c) { return c.checked; })
                ? 'Desmarcar todos' : 'Marcar todos';
        };
        btn.addEventListener('click', function () {
            const todas = casillas();
            const marcar = !todas.every(function (c) { return c.checked; });
            todas.forEach(function (c) { c.checked = marcar; });
            actualizarTexto();
        });
        grupo.addEventListener('change', actualizarTexto);
        actualizarTexto();
    });

    // ── El momento: hora en vivo, saludo y línea del día ───────────
    // Usa la hora del dispositivo del usuario. El servidor ya dejó un
    // valor inicial, así que sin JS la pantalla igual se ve bien.
    const horas = document.querySelectorAll('[data-momento="hora"]');
    const saludos = document.querySelectorAll('[data-momento="saludo"]');
    const lineas = document.querySelectorAll('[data-momento="linea"]');

    function saludoPara(h) {
        if (h >= 6 && h < 13) return 'Buen día';
        if (h >= 13 && h < 20) return 'Buenas tardes';
        return 'Buenas noches';
    }

    function actualizarMomento() {
        const ahora = new Date();
        const h = ahora.getHours();
        const texto = String(h).padStart(2, '0') + ':' + String(ahora.getMinutes()).padStart(2, '0');
        horas.forEach(function (el) { el.textContent = texto; el.setAttribute('datetime', texto); });
        saludos.forEach(function (el) { el.textContent = saludoPara(h); });
        const avance = ((h * 60 + ahora.getMinutes()) / 1440) * 100;
        lineas.forEach(function (el) { el.style.setProperty('--avance-dia', avance.toFixed(2) + '%'); });
    }

    if (horas.length || saludos.length || lineas.length) {
        actualizarMomento();
        // Se sincroniza con el cambio de minuto
        setTimeout(function () {
            actualizarMomento();
            setInterval(actualizarMomento, 60000);
        }, (60 - new Date().getSeconds()) * 1000);
    }
})();
