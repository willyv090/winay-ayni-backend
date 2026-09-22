from flask import Blueprint, request, jsonify

from app.services.metodo_pago_service import MetodoPagoService


metodo_pago_bp = Blueprint(
    "metodo_pago",
    __name__,
    url_prefix="/api/metodos-pago"
)


# ==========================================
# CREAR
# ==========================================

@metodo_pago_bp.route("", methods=["POST"])
def crear_metodo_pago():

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "No se enviaron datos."
        }), 400

    respuesta, codigo = MetodoPagoService.crear_metodo_pago(
        nombre=data.get("nombre"),
        descripcion=data.get("descripcion")
    )

    return jsonify(respuesta), codigo


# ==========================================
# LISTAR
# ==========================================

@metodo_pago_bp.route("", methods=["GET"])
def listar_metodos_pago():

    estado = request.args.get("estado")

    if estado is not None:

        if estado.lower() == "true":
            estado = True

        elif estado.lower() == "false":
            estado = False

        else:
            return jsonify({
                "error": "El parámetro estado debe ser true o false."
            }), 400

    respuesta, codigo = MetodoPagoService.listar_metodos_pago(
        estado=estado
    )

    return jsonify(respuesta), codigo


# ==========================================
# OBTENER UNO
# ==========================================

@metodo_pago_bp.route(
    "/<int:id_metodo>",
    methods=["GET"]
)
def obtener_metodo_pago(id_metodo):

    respuesta, codigo = MetodoPagoService.obtener_metodo_pago(
        id_metodo
    )

    return jsonify(respuesta), codigo


# ==========================================
# EDITAR
# ==========================================

@metodo_pago_bp.route(
    "/<int:id_metodo>",
    methods=["PUT"]
)
def editar_metodo_pago(id_metodo):

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "No se enviaron datos."
        }), 400

    respuesta, codigo = MetodoPagoService.editar_metodo_pago(
        id_metodo=id_metodo,
        nombre=data.get("nombre"),
        descripcion=data.get("descripcion")
    )

    return jsonify(respuesta), codigo


# ==========================================
# DESACTIVAR
# ==========================================

@metodo_pago_bp.route(
    "/<int:id_metodo>",
    methods=["DELETE"]
)
def eliminar_metodo_pago(id_metodo):

    respuesta, codigo = MetodoPagoService.eliminar_metodo_pago(
        id_metodo
    )

    return jsonify(respuesta), codigo


# ==========================================
# REACTIVAR
# ==========================================

@metodo_pago_bp.route(
    "/<int:id_metodo>/reactivar",
    methods=["PUT"]
)
def reactivar_metodo_pago(id_metodo):

    respuesta, codigo = MetodoPagoService.reactivar_metodo_pago(
        id_metodo
    )

    return jsonify(respuesta), codigo