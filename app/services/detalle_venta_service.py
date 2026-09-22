from decimal import Decimal

from app.extensions import db

from app.models.venta import Venta
from app.models.detalle_venta import DetalleVenta
from app.models.jornada_producto import JornadaProducto


class DetalleVentaService:

    # ==========================================
    # RECALCULAR TOTAL DE VENTA
    # ==========================================

    @staticmethod
    def _recalcular_total(venta):

        db.session.flush()

        total = db.session.query(
            db.func.coalesce(
                db.func.sum(DetalleVenta.subtotal),
                0
            )
        ).filter(
            DetalleVenta.venta_id_venta == venta.id_venta
        ).scalar()

        venta.total = Decimal(str(total))

    # ==========================================
    # CONVERTIR DETALLE A JSON
    # ==========================================

    @staticmethod
    def _detalle_json(detalle):

        precio = Decimal(detalle.precio_u)
        rebaja = Decimal(detalle.rebaja_aplicada)
        subtotal = Decimal(detalle.subtotal)

        producto = detalle.jornada_producto.producto

        return {
            "id": detalle.id_detalle,
            "cantidad": detalle.cantidad,
            "precio_u": float(precio),
            "rebaja": float(rebaja),
            "precio_final": float(precio - rebaja),
            "subtotal": float(subtotal),

            "producto": {
                "id": producto.id_prod,
                "nombre": producto.nombre
            },

            "jornada_producto": {
                "id": detalle.jornada_producto.id_jor_prod
            }
        }

    # ==========================================
    # AGREGAR DETALLE
    # ==========================================

    @staticmethod
    def agregar_detalles(id_venta, detalles):

        venta = Venta.query.get(id_venta)

        if not venta:
            return {
                "error": "La venta no existe."
            }, 404

        if not venta.jornada_cajero.jornada.estado:
            return {
                "error": "No se puede modificar una venta de una jornada finalizada."
            }, 400

        if not isinstance(detalles, list) or len(detalles) == 0:
            return {
                "error": "Debe enviar al menos un detalle de venta."
            }, 400

        jornada_id = venta.jornada_cajero.jornada_id_jornada

        detalles_preparados = []
        ids_recibidos = set()

        try:

            # ============================
            # VALIDAR TODOS PRIMERO
            # ============================

            for item in detalles:

                id_jornada_producto = item.get(
                    "id_jornada_producto"
                )

                cantidad = item.get("cantidad")

                if not id_jornada_producto:
                    return {
                        "error": "Todos los detalles deben tener id_jornada_producto."
                    }, 400

                try:
                    cantidad = int(cantidad)

                except (TypeError, ValueError):
                    return {
                        "error": "La cantidad debe ser un número entero."
                    }, 400

                if cantidad <= 0:
                    return {
                        "error": "La cantidad debe ser mayor a cero."
                    }, 400

                # Evitar producto repetido en el mismo JSON
                if id_jornada_producto in ids_recibidos:
                    return {
                        "error": f"El producto de jornada {id_jornada_producto} está repetido."
                    }, 400

                ids_recibidos.add(id_jornada_producto)

                jornada_producto = JornadaProducto.query.get(
                    id_jornada_producto
                )

                if not jornada_producto:
                    return {
                        "error": f"El producto de jornada {id_jornada_producto} no existe."
                    }, 404

                if not jornada_producto.estado:
                    return {
                        "error": f"El producto de jornada {id_jornada_producto} no está habilitado."
                    }, 400

                # Debe ser de la misma jornada
                if jornada_producto.jornada_id_jornada != jornada_id:
                    return {
                        "error": "Uno o más productos no pertenecen a la jornada de esta venta."
                    }, 400

                producto = jornada_producto.producto

                if not producto.estado:
                    return {
                        "error": f"El producto '{producto.nombre}' se encuentra inactivo."
                    }, 400

                if producto.cantidad < cantidad:
                    return {
                        "error": f"No existe stock suficiente para '{producto.nombre}'.",
                        "stock_disponible": producto.cantidad
                    }, 400

                # Comprobar que no esté agregado previamente
                detalle_existente = DetalleVenta.query.filter_by(
                    venta_id_venta=id_venta,
                    jornada_producto_id_jor_prod=id_jornada_producto
                ).first()

                if detalle_existente:
                    return {
                        "error": f"El producto '{producto.nombre}' ya está agregado a esta venta."
                    }, 409

                precio = Decimal(producto.precio_u)

                rebaja = (
                    Decimal(producto.rebaja)
                    if producto.rebaja is not None
                    else Decimal("0")
                )

                precio_final = precio - rebaja

                subtotal = precio_final * cantidad

                detalles_preparados.append({
                    "jornada_producto": jornada_producto,
                    "producto": producto,
                    "cantidad": cantidad,
                    "precio": precio,
                    "rebaja": rebaja,
                    "subtotal": subtotal
                })

            # ============================
            # TODO ES VÁLIDO → GUARDAR
            # ============================

            nuevos_detalles = []

            for item in detalles_preparados:

                nuevo_detalle = DetalleVenta(
                    cantidad=item["cantidad"],
                    precio_u=item["precio"],
                    rebaja_aplicada=item["rebaja"],
                    subtotal=item["subtotal"],
                    venta_id_venta=id_venta,
                    jornada_producto_id_jor_prod=(
                        item["jornada_producto"].id_jor_prod
                    )
                )

                db.session.add(nuevo_detalle)

                # Descontar stock
                item["producto"].cantidad -= item["cantidad"]

                nuevos_detalles.append(nuevo_detalle)

            db.session.flush()

            # Recalcular total de toda la venta
            DetalleVentaService._recalcular_total(
                venta
            )

            db.session.commit()

            return {
                "mensaje": "Productos agregados a la venta correctamente.",
                "detalles": [
                    DetalleVentaService._detalle_json(detalle)
                    for detalle in nuevos_detalles
                ],
                "total_venta": float(venta.total)
            }, 201

        except Exception as e:

            db.session.rollback()

            return {
                "error": "No se pudieron registrar los detalles de la venta.",
                "detalle": str(e)
            }, 500
    # ==========================================
    # LISTAR DETALLES DE UNA VENTA
    # ==========================================

    @staticmethod
    def listar_detalles(id_venta):

        venta = Venta.query.get(id_venta)

        if not venta:
            return {
                "error": "La venta no existe."
            }, 404

        detalles = DetalleVenta.query.filter_by(
            venta_id_venta=id_venta
        ).order_by(
            DetalleVenta.id_detalle
        ).all()

        resultado = [
            DetalleVentaService._detalle_json(detalle)
            for detalle in detalles
        ]

        return {
            "venta": {
                "id": venta.id_venta,
                "fecha": venta.fecha.isoformat(),
                "total": float(venta.total)
            },
            "detalles": resultado
        }, 200

    # ==========================================
    # CAMBIAR CANTIDAD
    # ==========================================

    @staticmethod
    def editar_cantidad(
        id_venta,
        id_detalle,
        cantidad
    ):

        venta = Venta.query.get(id_venta)

        if not venta:
            return {
                "error": "La venta no existe."
            }, 404

        if not venta.jornada_cajero.jornada.estado:
            return {
                "error": "No se puede modificar una venta de una jornada finalizada."
            }, 400

        detalle = DetalleVenta.query.filter_by(
            id_detalle=id_detalle,
            venta_id_venta=id_venta
        ).first()

        if not detalle:
            return {
                "error": "El detalle de venta no existe."
            }, 404

        try:
            cantidad = int(cantidad)
        except (TypeError, ValueError):
            return {
                "error": "La cantidad debe ser un número entero."
            }, 400

        if cantidad <= 0:
            return {
                "error": "La cantidad debe ser mayor a cero."
            }, 400

        producto = detalle.jornada_producto.producto

        cantidad_anterior = detalle.cantidad

        diferencia = cantidad - cantidad_anterior

        # Si aumenta la cantidad, verificar stock adicional
        if diferencia > 0 and producto.cantidad < diferencia:
            return {
                "error": "No existe stock suficiente.",
                "stock_disponible": producto.cantidad
            }, 400

        try:

            # diferencia positiva → descontar
            # diferencia negativa → devolver stock
            producto.cantidad -= diferencia

            detalle.cantidad = cantidad

            precio = Decimal(detalle.precio_u)
            rebaja = Decimal(detalle.rebaja_aplicada)

            detalle.subtotal = (
                precio - rebaja
            ) * cantidad

            db.session.flush()

            DetalleVentaService._recalcular_total(
                venta
            )

            db.session.commit()

            return {
                "mensaje": "Cantidad actualizada correctamente.",
                "detalle": DetalleVentaService._detalle_json(
                    detalle
                ),
                "total_venta": float(venta.total)
            }, 200

        except Exception as e:

            db.session.rollback()

            return {
                "error": "No se pudo actualizar el detalle.",
                "detalle": str(e)
            }, 500

    # ==========================================
    # QUITAR PRODUCTO DE LA VENTA
    # ==========================================

    @staticmethod
    def eliminar_detalle(
        id_venta,
        id_detalle
    ):

        venta = Venta.query.get(id_venta)

        if not venta:
            return {
                "error": "La venta no existe."
            }, 404

        if not venta.jornada_cajero.jornada.estado:
            return {
                "error": "No se puede modificar una venta de una jornada finalizada."
            }, 400

        detalle = DetalleVenta.query.filter_by(
            id_detalle=id_detalle,
            venta_id_venta=id_venta
        ).first()

        if not detalle:
            return {
                "error": "El detalle de venta no existe."
            }, 404

        try:

            producto = detalle.jornada_producto.producto

            # Devolver el stock
            producto.cantidad += detalle.cantidad

            db.session.delete(detalle)

            db.session.flush()

            DetalleVentaService._recalcular_total(
                venta
            )

            db.session.commit()

            return {
                "mensaje": "Producto retirado de la venta correctamente.",
                "total_venta": float(venta.total)
            }, 200

        except Exception as e:

            db.session.rollback()

            return {
                "error": "No se pudo eliminar el detalle.",
                "detalle": str(e)
            }, 500