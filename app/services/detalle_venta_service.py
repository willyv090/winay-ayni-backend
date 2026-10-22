from decimal import Decimal
from app.extensions import db
from app.models.venta import Venta
from app.models.detalle_venta import DetalleVenta
from app.models.producto import Producto
from app.models.jornada_producto import JornadaProducto
from app.services.venta_service import VentaService, VentaError


class DetalleVentaService:
    @staticmethod
    def _recalcular_total(venta):
        db.session.flush()
        venta.total = db.session.query(db.func.coalesce(db.func.sum(DetalleVenta.subtotal), 0)).filter(
            DetalleVenta.venta_id_venta == venta.id_venta).scalar()
        if venta.total > Decimal("99999999.99"):
            raise VentaError("El total supera el límite permitido.")

    @staticmethod
    def _detalle_json(detalle):
        return {
            "id": detalle.id_detalle, "cantidad": detalle.cantidad,
            "precio_u": float(detalle.precio_u), "rebaja": float(detalle.rebaja_aplicada),
            "precio_final": float(detalle.precio_u - detalle.rebaja_aplicada),
            "subtotal": float(detalle.subtotal),
            "producto": {"id": detalle.producto.id_prod, "nombre": detalle.producto.nombre,
                         "empresa_nombre": detalle.producto.empresa.nombre,
                         "empresa_id": detalle.producto.empresa_id_empresa},
            "jornada_producto": {"id": detalle.jornada_producto_id_jor_prod} if detalle.jornada_producto_id_jor_prod else None
        }

    @staticmethod
    def _venta_escritura(id_venta, id_persona):
        venta = Venta.query.filter_by(id_venta=id_venta).with_for_update().first()
        if not venta:
            raise VentaError("Venta no disponible.", 404)
        contexto = VentaService.validar_escritura(venta, id_persona)
        return venta, contexto

    @staticmethod
    def _producto_valido(venta, producto, contexto, asignacion=None):
        if not producto.estado or not producto.empresa.estado:
            raise VentaError("El producto o su empresa se encuentra inactivo.")
        if venta.tipo == "INDEPENDIENTE":
            if asignacion is not None or producto.empresa_id_empresa not in contexto["empresas"]:
                raise VentaError("El producto no pertenece a una empresa vinculada.", 403)
        elif (not asignacion or not asignacion.estado
              or asignacion.producto_id_prod != producto.id_prod
              or asignacion.jornada_id_jornada != venta.jornada_cajero.jornada_id_jornada):
            raise VentaError("El producto no está habilitado en la jornada de la venta.")

    @staticmethod
    def _agregar(venta, detalles, contexto):
        if not isinstance(detalles, list) or not detalles:
            raise VentaError("Debe enviar una lista no vacía de detalles.")
        preparados = []
        recibidos = set()
        empresas = {d.producto.empresa_id_empresa for d in DetalleVenta.query.filter_by(venta_id_venta=venta.id_venta).all()}
        for item in detalles:
            if not isinstance(item, dict):
                raise VentaError("Cada detalle debe ser un objeto.")
            cantidad = VentaService.entero(item.get("cantidad"), "Cantidad")
            jp = None
            if venta.tipo == "JORNADA":
                jid = VentaService.entero(item.get("id_jornada_producto"), "Producto de jornada")
                jp = db.session.get(JornadaProducto, jid)
                if not jp:
                    raise VentaError("Producto de jornada no disponible.", 404)
                pid = jp.producto_id_prod
                if item.get("id_producto") is not None and VentaService.entero(item["id_producto"], "Producto") != pid:
                    raise VentaError("El producto no coincide con su asignación.")
            else:
                if item.get("id_jornada_producto") is not None:
                    raise VentaError("Una venta independiente no lleva productos de jornada.")
                pid = VentaService.entero(item.get("id_producto"), "Producto")
            if pid in recibidos:
                raise VentaError("No repita un producto en la misma solicitud.")
            recibidos.add(pid)
            aplicar = item.get("aplicar_descuento", True)
            if not isinstance(aplicar, bool):
                raise VentaError("aplicar_descuento debe ser verdadero o falso.")
            preparados.append((pid, cantidad, jp, aplicar))
        nuevos = []
        # Orden estable de bloqueo para ventas concurrentes con varios productos.
        for pid, cantidad, jp, aplicar in sorted(preparados, key=lambda x: x[0]):
            producto = Producto.query.filter_by(id_prod=pid).with_for_update().populate_existing().first()
            if not producto:
                raise VentaError("Producto no disponible.", 404)
            DetalleVentaService._producto_valido(venta, producto, contexto, jp)
            empresas.add(producto.empresa_id_empresa)
            if venta.tipo == "INDEPENDIENTE" and len(empresas) > 1:
                raise VentaError("Una venta independiente debe pertenecer a una sola empresa.")
            if DetalleVenta.query.filter_by(venta_id_venta=venta.id_venta, producto_id_prod=pid).first():
                raise VentaError("El producto ya está agregado a la venta.", 409)
            if producto.cantidad < cantidad:
                raise VentaError("No existe stock suficiente.")
            precio, rebaja = Decimal(producto.precio_u), Decimal(producto.rebaja or 0)
            if precio <= 0 or rebaja < 0 or rebaja > precio:
                raise VentaError("El producto tiene un precio o rebaja inválidos.")
            rebaja = rebaja if aplicar else Decimal('0')
            detalle = DetalleVenta(cantidad=cantidad, precio_u=precio, rebaja_aplicada=rebaja,
                subtotal=(precio-rebaja)*cantidad, venta_id_venta=venta.id_venta,
                producto_id_prod=pid, jornada_producto_id_jor_prod=jp.id_jor_prod if jp else None)
            if detalle.subtotal > Decimal("99999999.99"):
                raise VentaError("El subtotal supera el límite permitido.")
            producto.cantidad -= cantidad
            db.session.add(detalle)
            nuevos.append(detalle)
        DetalleVentaService._recalcular_total(venta)
        return nuevos

    @staticmethod
    def agregar_detalles(id_venta, detalles, id_persona=None):
        def operacion():
            venta, contexto = DetalleVentaService._venta_escritura(id_venta, id_persona)
            nuevos = DetalleVentaService._agregar(venta, detalles, contexto)
            return {"mensaje": "Productos agregados correctamente.",
                    "detalles": [DetalleVentaService._detalle_json(d) for d in nuevos],
                    "total_venta": float(venta.total)}, 201
        return VentaService.ejecutar(operacion, escritura=True)

    @staticmethod
    def listar_detalles(id_venta, usuario_id=None, rol=None, id_empresa=None):
        def operacion():
            contexto = VentaService.contexto(usuario_id, rol)
            venta = VentaService.consultar(id_venta, contexto)
            eid = VentaService.entero(id_empresa, "Empresa") if id_empresa is not None else None
            if eid is not None and contexto["rol"] == "EMPRENDEDOR" and eid not in contexto["empresas"]:
                raise VentaError("Empresa no disponible.", 404)
            detalles = VentaService.detalles_visibles(venta, contexto, eid)
            if eid is not None and not detalles:
                raise VentaError("Venta no disponible para esta empresa.", 404)
            return {"venta": VentaService._venta_json(venta, contexto, eid),
                    "detalles": [DetalleVentaService._detalle_json(d) for d in detalles]}, 200
        return VentaService.ejecutar(operacion)

    @staticmethod
    def _detalle_bloqueado(venta, id_detalle):
        detalle = DetalleVenta.query.filter_by(id_detalle=id_detalle, venta_id_venta=venta.id_venta).first()
        if not detalle:
            raise VentaError("Detalle no disponible.", 404)
        producto = Producto.query.filter_by(id_prod=detalle.producto_id_prod).with_for_update().populate_existing().first()
        return detalle, producto

    @staticmethod
    def editar_cantidad(id_venta, id_detalle, cantidad, id_persona=None):
        def operacion():
            nueva = VentaService.entero(cantidad, "Cantidad")
            venta, contexto = DetalleVentaService._venta_escritura(id_venta, id_persona)
            detalle, producto = DetalleVentaService._detalle_bloqueado(venta, id_detalle)
            diferencia = nueva - detalle.cantidad
            if diferencia > 0:
                DetalleVentaService._producto_valido(venta, producto, contexto, detalle.jornada_producto)
                if producto.cantidad < diferencia:
                    raise VentaError("No existe stock suficiente.")
            producto.cantidad -= diferencia
            detalle.cantidad = nueva
            # Conservar los precios que se aplicaron originalmente.
            detalle.subtotal = (detalle.precio_u - detalle.rebaja_aplicada) * nueva
            if detalle.subtotal > Decimal("99999999.99"):
                raise VentaError("El subtotal supera el límite permitido.")
            DetalleVentaService._recalcular_total(venta)
            return {"mensaje": "Cantidad actualizada.", "detalle": DetalleVentaService._detalle_json(detalle),
                    "total_venta": float(venta.total)}, 200
        return VentaService.ejecutar(operacion, escritura=True)

    @staticmethod
    def eliminar_detalle(id_venta, id_detalle, id_persona=None):
        def operacion():
            venta, contexto = DetalleVentaService._venta_escritura(id_venta, id_persona)
            detalle, producto = DetalleVentaService._detalle_bloqueado(venta, id_detalle)
            producto.cantidad += detalle.cantidad
            db.session.delete(detalle)
            DetalleVentaService._recalcular_total(venta)
            return {"mensaje": "Detalle retirado y stock devuelto.", "total_venta": float(venta.total)}, 200
        return VentaService.ejecutar(operacion, escritura=True)
