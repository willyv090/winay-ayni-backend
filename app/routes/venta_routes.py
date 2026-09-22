from flask import Blueprint, request, jsonify

from app.services.venta_service import VentaService


venta_bp = Blueprint(
    "venta",
    __name__,
    url_prefix="/api/ventas"
)


# ==========================================
# CREAR / INICIAR VENTA
# ==========================================

@venta_bp.route("", methods=["POST"])
def crear_venta():

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "No se enviaron datos."
        }), 400

    respuesta, codigo = VentaService.crear_venta(
        id_jornada_cajero=data.get("id_jornada_cajero"),
        id_metodo_pago=data.get("id_metodo_pago")
    )

    return jsonify(respuesta), codigo


# ==========================================
# LISTAR
# ==========================================

@venta_bp.route("", methods=["GET"])
def listar_ventas():

    id_jornada = request.args.get(
        "id_jornada",
        type=int
    )

    id_persona = request.args.get(
        "id_persona",
        type=int
    )

    id_metodo_pago = request.args.get(
        "id_metodo_pago",
        type=int
    )

    respuesta, codigo = VentaService.listar_ventas(
        id_jornada=id_jornada,
        id_persona=id_persona,
        id_metodo_pago=id_metodo_pago
    )

    return jsonify(respuesta), codigo


# ==========================================
# OBTENER POR ID
# ==========================================

@venta_bp.route(
    "/<int:id_venta>",
    methods=["GET"]
)
def obtener_venta(id_venta):

    respuesta, codigo = VentaService.obtener_venta(
        id_venta
    )

    return jsonify(respuesta), codigo