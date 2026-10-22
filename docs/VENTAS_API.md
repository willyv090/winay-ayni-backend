# Ventas después de la ampliación del modelo

Los endpoints existentes de ventas y detalles requieren Authorization: Bearer <token>.
No se crean rutas ni servicios adicionales. Estas operaciones aún no están conectadas al frontend.

## Registrar una venta independiente completa

POST /api/ventas

```json
{
  "tipo": "INDEPENDIENTE",
  "id_metodo_pago": 1,
  "fecha": "2026-10-15T15:30:00",
  "detalles": [
    { "id_producto": 25, "cantidad": 2 }
  ]
}
```

IDs ilustrativos: sustituir por registros reales. La identidad responsable procede del JWT.
Exige rol EMPRENDEDOR activo y vínculo vigente con la empresa. Todos los productos de
una venta independiente deben pertenecer a una sola empresa activa.
Fecha es opcional y representa hora local sin offset, conforme al esquema actual.
fecha_registro se obtiene del default de la base; no se recibe del cliente.

## Registrar una venta de jornada completa

POST /api/ventas

```json
{
  "tipo": "JORNADA",
  "id_jornada_cajero": 4,
  "id_metodo_pago": 1,
  "detalles": [
    { "id_jornada_producto": 12, "cantidad": 2 }
  ]
}
```

Exige CAJERO activo y su propia asignación activa en jornada abierta.
Tipo omitido conserva JORNADA por compatibilidad. Para jornadas sigue disponible iniciar
sin detalles y agregarlos después. Para venta independiente se exigen detalles al crear.
Se recomienda el POST completo: venta, detalles, total y descuento de stock se confirman
en una sola transacción; si falla un detalle, se revierte todo.

Los precios, rebajas y subtotales se calculan en servidor; no se aceptan importes del cliente.
Los bloqueos de fila serializan escrituras sobre la misma venta y stock de productos en PostgreSQL.
No hay clave de idempotencia: no reintentar automáticamente un POST tras un timeout sin comprobar el resultado.

## Consultar

- GET /api/ventas
- GET /api/ventas/{id}
- GET /api/ventas/{id}/detalles

Filtros de listado: tipo, id_jornada, id_persona, id_metodo_pago, id_empresa.
Para cuentas multirol enviar rol=ADMINISTRADOR, rol=CAJERO o rol=EMPRENDEDOR.
El rol se comprueba contra la base. Sin parámetro se prioriza administrador, emprendedor, cajero.

Administrador consulta todas las ventas; cajero consulta sus ventas de jornada;
emprendedor consulta solamente los detalles de sus empresas vinculadas.
En las consultas del emprendedor, total representa únicamente sus detalles visibles.
Con id_empresa, total representa solo esa empresa.
alcance_total indica VENTA, MIS_EMPRESAS o EMPRESA. No sumar una venta completa por cada empresa.
Ventas independientes devuelven jornada=null y cajero=null, pero siempre responsable.

## Modificar detalles

- POST /api/ventas/{id}/detalles con {"detalles": [...]}
- PUT /api/ventas/{id}/detalles/{detalle} con {"cantidad": 3}
- DELETE /api/ventas/{id}/detalles/{detalle}

Solo el responsable puede modificar. Para jornada se exige asignación vigente y jornada abierta.
Para independiente se exige rol y vínculo vigente con empresa activa.
Aumentar requiere producto activo, asignación habilitada (si corresponde) y stock suficiente.
Reducir o retirar devuelve existencias, conserva precios históricos y recalcula el total.
No se permite repetir productos: editar cantidad del detalle existente.
El DELETE conserva la conducta anterior: elimina el detalle físicamente y devuelve stock;
no es una anulación contable ni un registro de auditoría. Quitar el último detalle deja total cero.
Un producto con ventas no puede cambiar de empresa, para conservar la atribución histórica.

## Verificación

Ejecutar desde el backend:
`./venv/Scripts/python.exe -m unittest discover -s tests -p "test_ventas.py" -v`

Las pruebas fuerzan SQLite en memoria, sin usar PostgreSQL ni datos reales.
El bloqueo concurrente de PostgreSQL necesita una prueba de integración en ese motor.


## Métricas independientes por empresa

GET /api/ventas/metricas/independientes?id_empresa=1&desde=2026-10-01&hasta=2026-10-31

Requiere JWT, rol emprendedor vigente y vínculo activo con la empresa, incluso para cuentas multirol.
Desde y hasta son opcionales, formato YYYY-MM-DD, ambos días incluidos.
Se filtra por fecha de venta, no fecha_registro. Solo cuenta tipo INDEPENDIENTE.
Empresas inactivas vinculadas y productos archivados conservan sus métricas históricas.

Respuesta: empresa, tipo, periodo, resumen y ranking.
Resumen: ventas (distintas con detalles), unidades_vendidas, total_vendido (suma de subtotales),
productos_vendidos (distintos), promedio_por_venta.
Ranking: los 10 primeros por unidades descendentes, luego importe descendente, luego ID ascendente
para desempate estable. Cada fila contiene posicion, producto, unidades_vendidas y total_vendido.
Los precios actuales no alteran los subtotales históricos; las modificaciones o eliminaciones de
detalles sí actualizan estos resultados. Las ventas sin detalles no se cuentan.

## Consultas y stock del emprendedor

- GET /api/ventas/metricas/ferias?id_empresa=ID&desde=YYYY-MM-DD&hasta=YYYY-MM-DD:
  mismo contrato que métricas independientes, con tipo JORNADA. Incluye ferias
  finalizadas y precios históricos; solo suma productos de la empresa vinculada.
- GET /api/ventas?rol=EMPRENDEDOR&id_empresa=ID: historial de ambos tipos.
- GET /api/ventas/ID/detalles?rol=EMPRENDEDOR&id_empresa=ID:
  detalle y total limitados a la empresa seleccionada, incluso con varias empresas propias.
- PUT /api/productos/ID/stock con { "ajuste": 5 } repone;
  con { "ajuste": -2 } retira. Requiere producto y empresa activos y pertenencia.
  Rechaza fracciones, booleanos, cero y stock negativo. No crea una venta ni un
  historial de movimientos. La interfaz no envía notas para conservar la descripción.
- Ventas y Consultas mantienen métricas como entrada y agregan la pestaña Historial.
  Los filtros de fecha/tipo del historial se aplican en frontend al listado recibido.

## Caja de jornada

- GET /api/jornadas/cajero/mias: JWT, rol CAJERO vigente, asignaciones activas y jornadas abiertas.
- GET /api/jornadas/ID/productos/caja: exige asignación propia activa; devuelve productos
  asignados activos de empresas activas, incluyendo sin stock para consulta.
- POST /api/ventas: tipo JORNADA, id_jornada_cajero, id_metodo_pago y detalles con
  id_jornada_producto/cantidad. Permite distintas empresas en una misma venta.
  La interfaz envía total_esperado; si difiere del importe calculado, responde 409 y
  revierte toda la venta y stock. Los precios siempre se calculan en el servidor.
- GET /api/ventas?rol=CAJERO y GET /api/ventas/ID/detalles?rol=CAJERO:
  solo ventas de jornada registradas por el usuario autenticado.
- Caja registra un pago recibido externamente; no integra una pasarela bancaria.
  El cálculo opcional de recibido/cambio es local y no persiste.
  Se mantiene el contrato anterior de ventas; no se requieren cambios de esquema.

## Métricas de administrador
GET /api/ventas/metricas/admin requiere JWT y rol ADMINISTRADOR activo.
Filtros opcionales: id_jornada, desde, hasta (YYYY-MM-DD, límites inclusivos).
Devuelve resumen (ventas distintas con detalles, unidades y total), top 10 empresas
por importe, top 10 productos por unidades, días con ventas y comparación de todas
las ferias. La comparación comparte las fechas, pero no el filtro id_jornada.
Solo incluye ventas JORNADA. Usa subtotales históricos, incluye productos archivados
y ferias finalizadas. Las ferias sin ventas aparecen con cero.
Una venta multiempresa cuenta una vez en resumen y una vez para cada empresa involucrada.
No requiere cambios de esquema.

## Ajuste de alcance sin cambios de base de datos (20/10/2026)

- No se incorporan historiales de cambio de cajero ni de movimientos de stock.
- Cada detalle admite aplicar_descuento booleano: false guarda rebaja_aplicada=0;
  true aplica el importe configurado por el emprendedor. La interfaz inicia sin descuento
  y envía siempre la elección. Por compatibilidad con clientes anteriores, omitir
  aplicar_descuento conserva el comportamiento anterior (aplicar la rebaja configurada).
  No se acepta un importe arbitrario enviado por el cliente. Ambos formularios envían total_esperado.
- GET /api/jornadas/ID/reporte, exclusivo ADMINISTRADOR, devuelve todas las empresas
  vinculadas a productos de la feria (incluidas asignaciones retiradas y ventas previas),
  ventas, unidades, importes por empresa y método de pago, productos y stock actual.
  No es una captura histórica de inventario al cierre.
- PUT /api/jornadas/ID/cerrar valida detalles, sumas por venta y total por empresas.
  Si hay inconsistencias devuelve 409 y conserva la jornada abierta.
  Si cuadra, guarda estado=false. DELETE /api/jornadas/ID utiliza la misma validación.
  El cierre y las escrituras de venta coordinan un bloqueo de la fila Jornada.
  Una feria sin ventas puede archivarse; una venta sin detalles impide cerrar.
- Reactivar permanece como excepción administrativa por error humano.
- Se utiliza la clave primaria como código único; se permite buscarla sin mostrar
  identificadores en las tarjetas de producto. Los nombres no se consideran únicos.
- Se conservan los importes históricos de ventas. Los reportes se calculan sobre las
  tablas existentes; no se crea snapshot ni tabla de cierre.
