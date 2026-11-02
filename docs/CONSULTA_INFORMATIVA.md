# Consulta informativa: inventario, ventas y ferias

GET /api/productos/consulta?rol=... devuelve empresas y jornadas autorizadas.
POST /api/productos/consulta requiere JWT y recibe rol, pregunta (1-700 caracteres),
buscar (hasta 100), id_empresa, id_jornada, desde/hasta YYYY-MM-DD y tipo
(JORNADA, INDEPENDIENTE o vacío). No se aceptan datos del catálogo del cliente.

## Alcance
Administrador: catálogo y ventas de los productos seleccionados.
Emprendedor: inventario y detalles de ventas de sus empresas con vínculo vigente,
incluyendo sus productos vendidos por cajeros. Nunca el total de otras empresas
aunque estén en la misma venta. Se respeta el rol activo en cuentas multirol.
Cajero: solo ventas realizadas por él en la feria seleccionada. Puede consultar una
feria finalizada o una asignación revocada si tiene ventas propias allí. En ese caso
solo recibe productos vendidos por él y stock/precio actuales nulos.
Sin ventas propias ni asignación activa, no puede acceder a la feria.

Incluye productos archivados con ventas históricas; no se pierden sus importes.
Las jornadas finalizadas son consultables por administrador y emprendedor autorizado.
Stock es actual compartido, nunca stock histórico de una feria.

## Cálculos
VentaService calcula cantidad de ventas distintas, unidades y suma de subtotales
históricos de DetalleVenta. No usa precio actual ni el total completo de una venta
con productos de otras empresas. Agrupa por producto, tipo, método de pago, feria
y vendedor mediante agregados SQL. Los totales globales cuentan cada venta una vez.
Una misma venta puede aparecer en varios productos: sus conteos no se suman.
Los ingresos incluyen descuentos realmente aplicados. No hay costos registrados,
por lo que ganancia_neta es null y no debe presentarse el ingreso como utilidad.
Sin fechas se consulta todo el historial. Fechas inclusivas por Venta.fecha; no
se interpretan automáticamente fechas relativas del texto: usar los filtros.
Cada pregunta es independiente y los filtros determinan el alcance de la respuesta.

## Worker y configuración
.env del backend: CLOUDFLARE_WORKER_URL HTTPS workers.dev y WINAY_API_KEY.
Reiniciar Flask tras cambiar configuración. No hay secretos en Vue.
Se mantiene el contrato del Worker existente: {pregunta, productos} -> {respuesta}.
Cada producto incorpora ventas; el primer producto transporta también el campo
resumen_del_conjunto_consultado, explícitamente global. No es una venta adicional.
No hace falta cambiar el código publicado de Cloudflare para esta ampliación.
Modelo solo redacta; no ejecuta APIs ni SQL. No hay cambios de base de datos.

## Límites y fallos
Hasta 30 productos y 19 KB de contexto. Si se excede, pide precisar filtros (422),
no trunca ventas silenciosamente. El campo buscar filtra producto/empresa literalmente.
Ante fallos del Worker, se muestra el catálogo y resumen real con generada=false.
Timeout backend 60 s; pantalla 70 s. No se reintenta automáticamente.

## Verificación
python -m unittest discover -s tests -p test_ventas.py -q
Pruebas en SQLite temporal con HTTP simulado: multirol, fechas, ventas mixtas,
pagos, precios históricos, archivos, ferias cerradas, ventas propias y ceros.
Frontend: npm run build. Prueba real del Worker solo con catálogo ficticio.
