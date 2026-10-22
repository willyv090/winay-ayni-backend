from datetime import date

from app.extensions import db
from app.models.jornada import Jornada


class JornadaService:

    # ==========================================
    # MÉTODOS AUXILIARES
    # ==========================================

    @staticmethod
    def _convertir_fecha(valor, nombre_campo):

        if not valor:
            raise ValueError(
                f"El campo {nombre_campo} es obligatorio."
            )

        if isinstance(valor, date):
            return valor

        try:
            return date.fromisoformat(valor)

        except (TypeError, ValueError):
            raise ValueError(
                f"El campo {nombre_campo} debe tener formato YYYY-MM-DD."
            )

    @staticmethod
    def _jornada_json(jornada):

        return {
            "id": jornada.id_jornada,
            "nombre": jornada.nombre,
            "direccion": jornada.direccion,
            "fecha_inicio": jornada.fecha_inicio.isoformat(),
            "fecha_fin": jornada.fecha_fin.isoformat(),
            "estado": jornada.estado,
        }

    # ==========================================
    # CREAR / ABRIR JORNADA
    # ==========================================

    @staticmethod
    def crear_jornada(
        nombre,
        direccion,
        fecha_inicio,
        fecha_fin
    ):

        if not nombre:
            return {
                "error": "El nombre de la jornada es obligatorio."
            }, 400

        if not direccion:
            return {
                "error": "La dirección es obligatoria."
            }, 400

        try:

            fecha_inicio = JornadaService._convertir_fecha(
                fecha_inicio,
                "fecha_inicio"
            )

            fecha_fin = JornadaService._convertir_fecha(
                fecha_fin,
                "fecha_fin"
            )

        except ValueError as e:
            return {
                "error": str(e)
            }, 400

        if fecha_fin < fecha_inicio:
            return {
                "error": "La fecha de fin no puede ser anterior a la fecha de inicio."
            }, 400

        try:

            nueva_jornada = Jornada(
                nombre=nombre.strip(),
                direccion=direccion.strip(),
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                estado=True,
            )

            db.session.add(nueva_jornada)
            db.session.commit()

            return {
                "mensaje": "Jornada creada correctamente.",
                "jornada": JornadaService._jornada_json(
                    nueva_jornada
                )
            }, 201

        except Exception as e:

            db.session.rollback()

            return {
                "error": "No se pudo crear la jornada.",
                "detalle": str(e)
            }, 500

    # ==========================================
    # LISTAR
    # ==========================================

    @staticmethod
    def listar_jornadas(
        estado=None,
        cerrada=None,
        fecha=None
    ):

        query = Jornada.query

        if estado is not None:
            query = query.filter(
                Jornada.estado == estado
            )

        if fecha:

            try:
                fecha = JornadaService._convertir_fecha(
                    fecha,
                    "fecha"
                )

            except ValueError as e:
                return {
                    "error": str(e)
                }, 400

            # Jornadas donde la fecha buscada esté
            # dentro del rango inicio-fin
            query = query.filter(
                Jornada.fecha_inicio <= fecha,
                Jornada.fecha_fin >= fecha
            )

        jornadas = query.order_by(
            Jornada.fecha_inicio.desc()
        ).all()

        resultado = [
            JornadaService._jornada_json(jornada)
            for jornada in jornadas
        ]

        return {
            "jornadas": resultado
        }, 200

    # ==========================================
    # OBTENER UNA JORNADA
    # ==========================================

    @staticmethod
    def obtener_jornada(id_jornada):

        jornada = Jornada.query.get(id_jornada)

        if not jornada:
            return {
                "error": "La jornada no existe."
            }, 404

        return {
            "jornada": JornadaService._jornada_json(
                jornada
            )
        }, 200

    # ==========================================
    # EDITAR
    # ==========================================

    @staticmethod
    def editar_jornada(
        id_jornada,
        nombre,
        direccion,
        fecha_inicio,
        fecha_fin
    ):

        jornada = Jornada.query.get(id_jornada)

        if not jornada:
            return {
                "error": "La jornada no existe."
            }, 404

        if not jornada.estado:
            return {
                "error": "No se puede modificar una jornada finalizada."
            }, 400
        
        if not nombre:
            return {
                "error": "El nombre de la jornada es obligatorio."
            }, 400

        if not direccion:
            return {
                "error": "La dirección es obligatoria."
            }, 400

        try:

            fecha_inicio = JornadaService._convertir_fecha(
                fecha_inicio,
                "fecha_inicio"
            )

            fecha_fin = JornadaService._convertir_fecha(
                fecha_fin,
                "fecha_fin"
            )

        except ValueError as e:
            return {
                "error": str(e)
            }, 400

        if fecha_fin < fecha_inicio:
            return {
                "error": "La fecha de fin no puede ser anterior a la fecha de inicio."
            }, 400

        try:

            jornada.nombre = nombre.strip()
            jornada.direccion = direccion.strip()
            jornada.fecha_inicio = fecha_inicio
            jornada.fecha_fin = fecha_fin

            db.session.commit()

            return {
                "mensaje": "Jornada actualizada correctamente.",
                "jornada": JornadaService._jornada_json(
                    jornada
                )
            }, 200

        except Exception as e:

            db.session.rollback()

            return {
                "error": "No se pudo actualizar la jornada.",
                "detalle": str(e)
            }, 500

    # ==========================================
    # CERRAR JORNADA
    # ==========================================

    @staticmethod
    def cerrar_jornada(id_jornada, usuario_id=None):
        from app.services.venta_service import VentaService, VentaError
        def operacion():
            VentaService.contexto(usuario_id, "ADMINISTRADOR")
            jornada = Jornada.query.filter_by(id_jornada=id_jornada).with_for_update().populate_existing().first()
            if not jornada:
                raise VentaError("La jornada no existe.", 404)
            if not jornada.estado:
                raise VentaError("La jornada ya está finalizada.")
            reporte = JornadaService._reporte(jornada)
            if not reporte["cuadra"]:
                return {"error": "No se puede cerrar: revise las inconsistencias del reporte.", "reporte": reporte}, 409
            jornada.estado = False
            reporte["jornada"] = JornadaService._jornada_json(jornada)
            return {"mensaje": "Jornada validada, finalizada y archivada.",
                    "jornada": JornadaService._jornada_json(jornada), "reporte": reporte}, 200
        return VentaService.ejecutar(operacion, escritura=True)

    # ==========================================
    # ELIMINACIÓN LÓGICA
    # ==========================================

    @staticmethod
    def eliminar_jornada(id_jornada):

        jornada = Jornada.query.get(id_jornada)

        if not jornada:
            return {
                "error": "La jornada no existe."
            }, 404

        if not jornada.estado:
            return {
                "error": "La jornada ya se encuentra inactiva."
            }, 400

        try:

            jornada.estado = False

            db.session.commit()

            return {
                "mensaje": "Jornada eliminada correctamente."
            }, 200

        except Exception as e:

            db.session.rollback()

            return {
                "error": "No se pudo eliminar la jornada.",
                "detalle": str(e)
            }, 500

    # ==========================================
    # REACTIVAR
    # ==========================================

    @staticmethod
    def reactivar_jornada(id_jornada):

        jornada = Jornada.query.get(id_jornada)

        if not jornada:
            return {
                "error": "La jornada no existe."
            }, 404

        if jornada.estado:
            return {
                "error": "La jornada ya se encuentra activa."
            }, 400

        try:

            jornada.estado = True

            db.session.commit()

            return {
                "mensaje": "Jornada reactivada correctamente.",
                "jornada": JornadaService._jornada_json(
                    jornada
                )
            }, 200

        except Exception as e:

            db.session.rollback()

            return {
                "error": "No se pudo reactivar la jornada.",
                "detalle": str(e)
            }, 500

    @staticmethod
    def _reporte(jornada):
        from decimal import Decimal
        from app.models.venta import Venta
        from app.models.detalle_venta import DetalleVenta
        from app.models.jornada_cajero import JornadaCajero
        from app.models.jornada_producto import JornadaProducto
        ventas = Venta.query.join(JornadaCajero).filter(
            Venta.tipo == "JORNADA", JornadaCajero.jornada_id_jornada == jornada.id_jornada
        ).order_by(Venta.id_venta).all()
        detalles = DetalleVenta.query.filter(DetalleVenta.venta_id_venta.in_([v.id_venta for v in ventas])).all()
        empresas, productos, pagos = {}, {}, {}
        sumas, conteos, problemas = {}, {}, []
        def incluir(p):
            eid = p.empresa_id_empresa
            if eid not in empresas:
                empresas[eid] = {"id": eid, "nombre": p.empresa.nombre, "total": Decimal(0), "unidades": 0, "ventas": set(), "pagos": {}}
            if p.id_prod not in productos:
                productos[p.id_prod] = {"id": p.id_prod, "nombre": p.nombre, "empresa_id": eid,
                    "stock_actual": p.cantidad, "estado": p.estado, "asignado": False, "unidades": 0, "total": Decimal(0)}
        for relacion in JornadaProducto.query.filter_by(jornada_id_jornada=jornada.id_jornada).all():
            incluir(relacion.producto)
            productos[relacion.producto_id_prod]["asignado"] |= relacion.estado
        por_id = {v.id_venta: v for v in ventas}
        for d in detalles:
            incluir(d.producto)
            v = por_id[d.venta_id_venta]
            importe = Decimal(d.subtotal)
            sumas[v.id_venta] = sumas.get(v.id_venta, Decimal(0)) + importe
            conteos[v.id_venta] = conteos.get(v.id_venta, 0) + 1
            if d.cantidad <= 0 or d.precio_u < 0 or d.rebaja_aplicada < 0 or d.rebaja_aplicada > d.precio_u or importe != (d.precio_u - d.rebaja_aplicada) * d.cantidad:
                problemas.append(f"Importes o cantidad inconsistentes en venta {v.id_venta}.")
            e = empresas[d.producto.empresa_id_empresa]
            e["total"] += importe
            e["unidades"] += d.cantidad
            e["ventas"].add(v.id_venta)
            nombre_pago = v.metodo_pago.nombre
            e["pagos"][nombre_pago] = e["pagos"].get(nombre_pago, Decimal(0)) + importe
            p = productos[d.producto_id_prod]
            p["total"] += importe
            p["unidades"] += d.cantidad
        total = Decimal(0)
        for v in ventas:
            total += v.total
            nombre = v.metodo_pago.nombre
            pagos[nombre] = pagos.get(nombre, Decimal(0)) + v.total
            if not conteos.get(v.id_venta):
                problemas.append(f"La venta {v.id_venta} no tiene productos.")
            if sumas.get(v.id_venta, Decimal(0)) != v.total:
                problemas.append(f"El total de la venta {v.id_venta} no coincide con sus productos.")
        total_empresas = sum((e["total"] for e in empresas.values()), Decimal(0))
        if total_empresas != total:
            problemas.append("La suma por empresas no coincide con el total general.")
        return {"jornada": JornadaService._jornada_json(jornada),
            "ventas": len(ventas), "total": float(total), "total_empresas": float(total_empresas),
            "diferencia": float(total - total_empresas), "cuadra": not problemas,
            "problemas": list(dict.fromkeys(problemas)),
            "metodos_pago": [{"nombre": n, "total": float(t)} for n,t in sorted(pagos.items())],
            "empresas": [{"id": e["id"], "nombre": e["nombre"], "ventas": len(e["ventas"]),
                "unidades": e["unidades"], "total": float(e["total"]),
                "metodos_pago": [{"nombre": n, "total": float(t)} for n,t in sorted(e["pagos"].items())]
                } for e in sorted(empresas.values(), key=lambda e: e["nombre"])],
            "productos": [{**p, "total": float(p["total"])} for p in sorted(productos.values(), key=lambda p: (p["empresa_id"], p["nombre"]))]}

    @staticmethod
    def reporte_jornada(id_jornada, usuario_id):
        from app.services.venta_service import VentaService, VentaError
        def operacion():
            VentaService.contexto(usuario_id, "ADMINISTRADOR")
            jornada = db.session.get(Jornada, id_jornada)
            if not jornada:
                raise VentaError("Jornada no disponible.", 404)
            return JornadaService._reporte(jornada), 200
        return VentaService.ejecutar(operacion)
