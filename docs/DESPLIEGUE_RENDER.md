# Render y Android

Preparación local; no se ha publicado el servicio ni conectado un repositorio.

1. Subir el backend a un repositorio privado sin .env, venv ni node_modules.
2. Render: New > Web Service > conectar repositorio y rama.
3. Language: Python 3. Root Directory: carpeta con run.py; vacío si está en la raíz.
4. Build: pip install -r requirements.txt
5. Start: gunicorn run:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120
6. Health Check Path: /health (solo comprueba el proceso, no la base de datos).
7. Variables: DATABASE_URL, SECRET_KEY, JWT_SECRET_KEY, CLOUDFLARE_WORKER_URL,
   WINAY_API_KEY, CORS_ORIGINS.
   CORS_ORIGINS=https://localhost,http://localhost:5173,http://127.0.0.1:5173
   Añadir origen exacto de la web si se publica, separado por coma.
8. Python usa la última revisión 3.13, definida en .python-version.
9. Deploy y revisar logs. La instalación en Linux se verificará durante ese build;
   la prueba local no sustituye la instalación remota de requirements.txt.
10. Comprobar /health, login y acceso a la base existente. No crear una base nueva.

Antes de abrir a usuarios reales falta revisar los permisos de todas las rutas
administrativas antiguas. Esta preparación no constituye una auditoría de acceso.

Frontend: .env.production.local con VITE_API_URL=https://SERVICIO.onrender.com
sin /api al final. npm run build incorpora esa URL. Nunca poner secretos de servidor.
Capacitor empaqueta dist. No usar server.url de desarrollo en el APK distribuido.
Android: npm run build; npx cap add android (una vez); npx cap sync android;
npx cap open android. Android Studio/SDK son necesarios para compilar.
El contenedor ahora usa el tamaño disponible y safe-area; comprobar teclado,
barra de estado, botón Atrás y confirmaciones en un dispositivo real.
