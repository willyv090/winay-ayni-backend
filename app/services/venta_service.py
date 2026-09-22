from datetime import datetime
from decimal import Decimal

from app.extensions import db

from app.models.venta import Venta
from app.models.jornada_cajero import JornadaCajero
from app.models.metodo_pago import MetodoPago


class VentaService:

    # ==========================================
    # CONVERTIR VENTA A JSON
    # ==========================================

    @staticmethod
    def _venta_json(venta):

        jornada_cajero = venta.jornada_cajero

        return {
            "id": venta.id_venta,
            "fecha": venta.fecha.isoformat(),
            "total": float(venta.total),
            "jornada": {
                "id": jornada_cajero.jornada.id_jornada,
                "nombre": jornada_cajero.jornada.nombre
            },
            "cajero": {
                "id": jornada_cajero.persona.id_per,
                "nombre": jornada_cajero.persona.nombre,
                "usuario": jornada_cajero.persona.usuario
            },
            "metodo_pago": {
                "id": venta.metodo_pago.id_metodos,
                "nombre": venta.metodo_pago.nombre
            }
        }

    # ==========================================
    # CREAR / INICIAR VENTA
    # ==========================================

    @staticmethod
    def crear_venta(
        id_jornada_cajero,
        id_metodo_pago
    ):

        # Buscar asignación cajero-jornada
        jornada_cajero = JornadaCajero.query.get(
            id_jornada_cajero
        )

        if not jornada_cajero:
            return {
                "error": "La asignación del cajero a la jornada no existe."
            }, 404

        # La relación cajero-jornada debe estar activa
        if not jornada_cajero.estado:
            return {
                "error": "El cajero ya no se encuentra asignado a esta jornada."
            }, 400

        # La persona también debe estar activa
        if not jornada_cajero.persona.estado:
            return {
                "error": "El cajero se encuentra inactivo."
            }, 400

        # La jornada debe seguir abierta
        if not jornada_cajero.jornada.estado:
            return {
                "error": "No se pueden registrar ventas en una jornada finalizada."
            }, 400

        # Verificar método de pago
        metodo_pago = MetodoPago.query.get(
            id_metodo_pago
        )

        if not metodo_pago:
            return {
                "error": "El método de pago no existe."
            }, 404

        if not metodo_pago.estado:
            return {
                "error": "El método de pago se encuentra inactivo."
            }, 400

        try:

            nueva_venta = Venta(
                fecha=datetime.now(),
                total=Decimal("0.00"),
                jornada_cajero_id_jor_caj=id_jornada_cajero,
                metodos_pago_id_metodos=id_metodo_pago
            )

            db.session.add(nueva_venta)
            db.session.commit()

            return {
                "mensaje": "Venta iniciada correctamente.",
                "venta": VentaService._venta_json(
                    nueva_venta
                )
            }, 201

        except Exception as e:

            db.session.rollback()

            return {
                "error": "No se pudo iniciar la venta.",
                "detalle": str(e)
            }, 500

    # ==========================================
    # LISTAR VENTAS
    # ==========================================

    @staticmethod
    def listar_ventas(
        id_jornada=None,
        id_persona=None,
        id_metodo_pago=None
    ):

        query = Venta.query.join(
            JornadaCajero,
            Venta.jornada_cajero_id_jor_caj
            == JornadaCajero.id_jor_caj
        )

        if id_jornada is not None:
            query = query.filter(
                JornadaCajero.jornada_id_jornada == id_jornada
            )

        if id_persona is not None:
            query = query.filter(
                JornadaCajero.persona_id_per == id_persona
            )

        if id_metodo_pago is not None:
            query = query.filter(
                Venta.metodos_pago_id_metodos == id_metodo_pago
            )

        ventas = query.order_by(
            Venta.fecha.desc()
        ).all()

        resultado = [
            VentaService._venta_json(venta)
            for venta in ventas
        ]

        return {
            "ventas": resultado
        }, 200

    # ==========================================
    # OBTENER UNA VENTA
    # ==========================================

    @staticmethod
    def obtener_venta(id_venta):

        venta = Venta.query.get(id_venta)

        if not venta:
            return {
                "error": "La venta no existe."
            }, 404

        return {
            "venta": VentaService._venta_json(
                venta
            )
        }, 200