from datetime import datetime
from decimal import Decimal
from app.extensions import db
from app.models.venta import Venta
from app.models.detalle_venta import DetalleVenta
from app.models.producto import Producto
from app.models.persona import Persona
from app.models.rol import Rol
from app.models.rol_persona import RolPersona
from app.models.jornada_cajero import JornadaCajero
from app.models.metodo_pago import MetodoPago
from app.services.empresa_service import EmpresaService


class VentaError(Exception):
    def __init__(self, mensaje, codigo=400):
        self.mensaje = mensaje
        self.codigo = codigo


class VentaService:
    @staticmethod
    def entero(valor, nombre):
        if isinstance(valor, bool) or not isinstance(valor, (str, int)):
            raise VentaError(f"{nombre} debe ser un entero positivo.")
        try:
            numero = int(valor)
        except (ValueError, TypeError):
            raise VentaError(f"{nombre} debe ser un entero positivo.")
        if numero <= 0 or numero > 2147483647:
            raise VentaError(f"{nombre} debe ser un entero positivo válido.")
        return numero

    @staticmethod
    def contexto(id_persona, rol=None):
        id_persona = VentaService.entero(id_persona, "Usuario")
        persona = db.session.get(Persona, id_persona)
        if not persona or not persona.estado:
            raise VentaError("Usuario inactivo o no disponible.", 403)
        roles = {r.nombre for r in Rol.query.join(
            RolPersona, RolPersona.rol_id_rol == Rol.id_rol
        ).filter(RolPersona.persona_id_per == id_persona,
                 RolPersona.estado.is_(True), Rol.estado.is_(True)).all()}
        if rol is None:
            rol = next((r for r in ("ADMINISTRADOR", "EMPRENDEDOR", "CAJERO") if r in roles), None)
        if rol not in roles or rol not in ("ADMINISTRADOR", "EMPRENDEDOR", "CAJERO"):
            raise VentaError("No tiene permisos para esta operación.", 403)
        empresas = {e.id_empresa for e in EmpresaService.consulta_propias(id_persona).all()}
        return {"persona": id_persona, "rol": rol, "empresas": empresas}

    @staticmethod
    def ejecutar(operacion, escritura=False):
        try:
            resultado = operacion()
            if escritura:
                db.session.commit()
            return resultado
        except VentaError as error:
            db.session.rollback()
            return {"error": error.mensaje}, error.codigo
        except Exception:
            db.session.rollback()
            from flask import current_app
            current_app.logger.exception("Error en operación de ventas")
            return {"error": "No se pudo completar la operación de ventas."}, 500

    @staticmethod
    def detalles_visibles(venta, contexto, id_empresa=None):
        query = DetalleVenta.query.filter_by(venta_id_venta=venta.id_venta).join(
            Producto, Producto.id_prod == DetalleVenta.producto_id_prod
        )
        if contexto["rol"] == "EMPRENDEDOR":
            query = query.filter(Producto.empresa_id_empresa.in_(contexto["empresas"]))
        if id_empresa is not None:
            query = query.filter(Producto.empresa_id_empresa == id_empresa)
        return query.order_by(DetalleVenta.id_detalle).all()

    @staticmethod
    def consultar(id_venta, contexto, bloquear=False):
        query = Venta.query.filter_by(id_venta=id_venta)
        if bloquear:
            query = query.with_for_update()
        venta = query.first()
        if venta is None:
            raise VentaError("Venta no disponible.", 404)
        if contexto["rol"] == "CAJERO" and (
            venta.tipo != "JORNADA" or venta.persona_id_per != contexto["persona"]
        ):
            raise VentaError("Venta no disponible.", 404)
        if contexto["rol"] == "EMPRENDEDOR" and not VentaService.detalles_visibles(venta, contexto):
            raise VentaError("Venta no disponible.", 404)
        return venta

    @staticmethod
    def validar_escritura(venta, id_persona):
        rol = "CAJERO" if venta.tipo == "JORNADA" else "EMPRENDEDOR"
        contexto = VentaService.contexto(id_persona, rol)
        if venta.persona_id_per != contexto["persona"]:
            raise VentaError("Solo el responsable puede modificar esta venta.", 403)
        if venta.tipo == "JORNADA":
            jc = venta.jornada_cajero
            if not jc or jc.persona_id_per != contexto["persona"] or not jc.estado:
                raise VentaError("La asignación del cajero ya no está activa.", 403)
            if not jc.jornada.estado:
                raise VentaError("La jornada está finalizada.")
        else:
            for detalle in DetalleVenta.query.filter_by(venta_id_venta=venta.id_venta).all():
                p = detalle.producto
                if p.empresa_id_empresa not in contexto["empresas"] or not p.empresa.estado:
                    raise VentaError("La empresa de la venta ya no está habilitada para su cuenta.", 403)
        return contexto

    @staticmethod
    def _venta_json(venta, contexto, id_empresa=None):
        jc = venta.jornada_cajero
        parcial = contexto["rol"] == "EMPRENDEDOR" or id_empresa is not None
        total = sum((d.subtotal for d in VentaService.detalles_visibles(venta, contexto, id_empresa)), Decimal("0")) if parcial else venta.total
        return {
            "id": venta.id_venta, "tipo": venta.tipo,
            "fecha": venta.fecha.isoformat(),
            "fecha_registro": venta.fecha_registro.isoformat() if venta.fecha_registro else None,
            "total": float(total), "alcance_total": "EMPRESA" if id_empresa else "MIS_EMPRESAS" if parcial else "VENTA",
            "responsable": {"id": venta.persona.id_per, "nombre": venta.persona.nombre},
            "jornada": {"id": jc.jornada.id_jornada, "nombre": jc.jornada.nombre} if jc else None,
            "cajero": {"id": jc.persona.id_per, "nombre": jc.persona.nombre, "usuario": jc.persona.usuario} if jc else None,
            "metodo_pago": {"id": venta.metodo_pago.id_metodos, "nombre": venta.metodo_pago.nombre}
        }

    @staticmethod
    def crear_venta(id_jornada_cajero=None, id_metodo_pago=None, tipo="JORNADA",
                    fecha=None, detalles=None, id_persona=None, total_esperado=None):
        def operacion():
            from app.services.detalle_venta_service import DetalleVentaService
            if tipo not in ("JORNADA", "INDEPENDIENTE"):
                raise VentaError("Tipo de venta inválido.")
            contexto = VentaService.contexto(id_persona, "CAJERO" if tipo == "JORNADA" else "EMPRENDEDOR")
            jc = None
            if tipo == "JORNADA":
                jid = VentaService.entero(id_jornada_cajero, "Asignación de cajero")
                jc = db.session.get(JornadaCajero, jid)
                if not jc or jc.persona_id_per != contexto["persona"] or not jc.estado:
                    raise VentaError("No tiene una asignación activa como cajero para esta venta.", 403)
                if not jc.jornada.estado:
                    raise VentaError("La jornada está finalizada.")
            elif id_jornada_cajero is not None:
                raise VentaError("Una venta independiente no lleva asignación de cajero.")
            if tipo == "INDEPENDIENTE" and not detalles:
                raise VentaError("La venta independiente debe incluir sus detalles.")
            pago = db.session.get(MetodoPago, VentaService.entero(id_metodo_pago, "Método de pago"))
            if not pago or not pago.estado:
                raise VentaError("Método de pago no disponible.", 404)
            momento = datetime.now()
            if fecha is not None:
                try:
                    momento = datetime.fromisoformat(fecha)
                    if momento.tzinfo is not None:
                        raise ValueError()
                except (ValueError, TypeError):
                    raise VentaError("La fecha debe ser ISO local, sin zona horaria.")
            venta = Venta(tipo=tipo, persona_id_per=contexto["persona"], fecha=momento,
                          total=Decimal("0"), jornada_cajero_id_jor_caj=jc.id_jor_caj if jc else None,
                          metodos_pago_id_metodos=pago.id_metodos)
            db.session.add(venta)
            db.session.flush()
            if detalles is not None:
                DetalleVentaService._agregar(venta, detalles, contexto)
            db.session.flush()
            if total_esperado is not None:
                try:
                    esperado = Decimal(str(total_esperado))
                    if not esperado.is_finite() or esperado < 0:
                        raise ValueError()
                except Exception:
                    raise VentaError("El total esperado debe ser un importe válido.")
                if esperado != venta.total:
                    raise VentaError("Los precios cambiaron. Actualice los productos y revise el cobro antes de confirmar.", 409)
            return {"mensaje": "Venta registrada correctamente.", "venta": VentaService._venta_json(venta, contexto)}, 201
        return VentaService.ejecutar(operacion, escritura=True)

    @staticmethod
    def listar_ventas(id_jornada=None, id_persona=None, id_metodo_pago=None,
                      tipo=None, id_empresa=None, usuario_id=None, rol=None):
        def operacion():
            contexto = VentaService.contexto(usuario_id, rol)
            query = Venta.query
            if contexto["rol"] == "CAJERO":
                query = query.filter(Venta.tipo == "JORNADA", Venta.persona_id_per == contexto["persona"])
            if contexto["rol"] == "EMPRENDEDOR" or id_empresa is not None:
                productos = Producto.query
                if contexto["rol"] == "EMPRENDEDOR":
                    productos = productos.filter(Producto.empresa_id_empresa.in_(contexto["empresas"]))
                if id_empresa is not None:
                    empresa = VentaService.entero(id_empresa, "Empresa")
                    if contexto["rol"] == "EMPRENDEDOR" and empresa not in contexto["empresas"]:
                        raise VentaError("Empresa no disponible.", 404)
                    productos = productos.filter(Producto.empresa_id_empresa == empresa)
                query = query.filter(Venta.id_venta.in_(db.session.query(DetalleVenta.venta_id_venta).filter(
                    DetalleVenta.producto_id_prod.in_(productos.with_entities(Producto.id_prod)))))
            if id_jornada is not None:
                query = query.join(JornadaCajero).filter(JornadaCajero.jornada_id_jornada == VentaService.entero(id_jornada, "Jornada"))
            if id_persona is not None:
                query = query.filter(Venta.persona_id_per == VentaService.entero(id_persona, "Persona"))
            if id_metodo_pago is not None:
                query = query.filter(Venta.metodos_pago_id_metodos == VentaService.entero(id_metodo_pago, "Método de pago"))
            if tipo is not None:
                if tipo not in ("JORNADA", "INDEPENDIENTE"):
                    raise VentaError("Tipo de venta inválido.")
                query = query.filter(Venta.tipo == tipo)
            empresa = int(id_empresa) if id_empresa is not None else None
            return {"ventas": [VentaService._venta_json(v, contexto, empresa) for v in query.order_by(Venta.fecha.desc(), Venta.id_venta.desc()).all()]}, 200
        return VentaService.ejecutar(operacion)

    @staticmethod
    def obtener_venta(id_venta, usuario_id=None, rol=None):
        def operacion():
            contexto = VentaService.contexto(usuario_id, rol)
            venta = VentaService.consultar(id_venta, contexto)
            return {"venta": VentaService._venta_json(venta, contexto)}, 200
        return VentaService.ejecutar(operacion)


    @staticmethod
    def metricas_independientes(id_empresa, usuario_id=None, desde=None, hasta=None):
        return VentaService.metricas_empresa(id_empresa, usuario_id, desde, hasta, "INDEPENDIENTE")

    @staticmethod
    def metricas_empresa(id_empresa, usuario_id=None, desde=None, hasta=None, tipo="JORNADA"):
        def operacion():
            from datetime import date, time, timedelta
            contexto = VentaService.contexto(usuario_id, "EMPRENDEDOR")
            eid = VentaService.entero(id_empresa, "Empresa")
            if eid not in contexto["empresas"]:
                raise VentaError("Empresa no disponible.", 404)
            empresa = EmpresaService.consulta_propias(contexto["persona"]).filter_by(id_empresa=eid).first()
            limites = {}
            for nombre, valor in (("desde", desde), ("hasta", hasta)):
                if valor:
                    try:
                        parsed = date.fromisoformat(valor)
                        if parsed.isoformat() != valor:
                            raise ValueError()
                        limites[nombre] = parsed
                    except (ValueError, TypeError):
                        raise VentaError("Las fechas deben tener formato YYYY-MM-DD.")
            if "desde" in limites and "hasta" in limites and limites["desde"] > limites["hasta"]:
                raise VentaError("La fecha inicial no puede ser posterior a la final.")
            query = db.session.query(DetalleVenta).join(
                Venta, Venta.id_venta == DetalleVenta.venta_id_venta
            ).join(Producto, Producto.id_prod == DetalleVenta.producto_id_prod).filter(
                Venta.tipo == tipo, Producto.empresa_id_empresa == eid
            )
            if "desde" in limites:
                query = query.filter(Venta.fecha >= datetime.combine(limites["desde"], time.min))
            if "hasta" in limites:
                if limites["hasta"] == date.max:
                    query = query.filter(Venta.fecha <= datetime.combine(date.max, time.max))
                else:
                    query = query.filter(Venta.fecha < datetime.combine(limites["hasta"] + timedelta(days=1), time.min))
            resumen = query.with_entities(
                db.func.count(db.distinct(Venta.id_venta)),
                db.func.coalesce(db.func.sum(DetalleVenta.cantidad), 0),
                db.func.coalesce(db.func.sum(DetalleVenta.subtotal), 0),
                db.func.count(db.distinct(DetalleVenta.producto_id_prod))
            ).one()
            unidades = db.func.sum(DetalleVenta.cantidad)
            importe = db.func.sum(DetalleVenta.subtotal)
            ranking = query.with_entities(
                Producto.id_prod, Producto.nombre, Producto.estado,
                unidades.label("unidades"), importe.label("importe")
            ).group_by(Producto.id_prod, Producto.nombre, Producto.estado).order_by(
                unidades.desc(), importe.desc(), Producto.id_prod.asc()
            ).limit(10).all()
            total = Decimal(str(resumen[2]))
            return {
                "empresa": {"id": empresa.id_empresa, "nombre": empresa.nombre, "estado": empresa.estado},
                "tipo": tipo,
                "periodo": {"desde": desde or None, "hasta": hasta or None},
                "resumen": {
                    "ventas": int(resumen[0]), "unidades_vendidas": int(resumen[1]),
                    "total_vendido": float(total), "productos_vendidos": int(resumen[3]),
                    "promedio_por_venta": float((total / resumen[0]).quantize(Decimal("0.01"))) if resumen[0] else 0
                },
                "ranking": [{"posicion": i, "producto": {"id": r.id_prod, "nombre": r.nombre, "estado": r.estado},
                             "unidades_vendidas": int(r.unidades), "total_vendido": float(r.importe)}
                            for i, r in enumerate(ranking, 1)]
            }, 200
        return VentaService.ejecutar(operacion)
