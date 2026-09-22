from flask import Blueprint, request, jsonify

from app.services.jornada_service import JornadaService


jornada_bp = Blueprint(
    "jornada",
    __name__,
    url_prefix="/api/jornadas"
)


# ==========================================
# CREAR
# ==========================================

@jornada_bp.route("", methods=["POST"])
def crear_jornada():

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "No se enviaron datos."
        }), 400

    respuesta, codigo = JornadaService.crear_jornada(
        nombre=data.get("nombre"),
        direccion=data.get("direccion"),
        fecha_inicio=data.get("fecha_inicio"),
        fecha_fin=data.get("fecha_fin")
    )

    return jsonify(respuesta), codigo


# ==========================================
# LISTAR
# ==========================================

@jornada_bp.route("", methods=["GET"])
def listar_jornadas():

    estado = request.args.get("estado")
    cerrada = request.args.get("cerrada")
    fecha = request.args.get("fecha")

    # Convertir query params true/false
    if estado is not None:

        if estado.lower() == "true":
            estado = True

        elif estado.lower() == "false":
            estado = False

        else:
            return jsonify({
                "error": "El parámetro estado debe ser true o false."
            }), 400

    if cerrada is not None:

        if cerrada.lower() == "true":
            cerrada = True

        elif cerrada.lower() == "false":
            cerrada = False

        else:
            return jsonify({
                "error": "El parámetro cerrada debe ser true o false."
            }), 400

    respuesta, codigo = JornadaService.listar_jornadas(
        estado=estado,
        cerrada=cerrada,
        fecha=fecha
    )

    return jsonify(respuesta), codigo


# ==========================================
# OBTENER POR ID
# ==========================================

@jornada_bp.route(
    "/<int:id_jornada>",
    methods=["GET"]
)
def obtener_jornada(id_jornada):

    respuesta, codigo = JornadaService.obtener_jornada(
        id_jornada
    )

    return jsonify(respuesta), codigo


# ==========================================
# EDITAR
# ==========================================

@jornada_bp.route(
    "/<int:id_jornada>",
    methods=["PUT"]
)
def editar_jornada(id_jornada):

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "No se enviaron datos."
        }), 400

    respuesta, codigo = JornadaService.editar_jornada(
        id_jornada=id_jornada,
        nombre=data.get("nombre"),
        direccion=data.get("direccion"),
        fecha_inicio=data.get("fecha_inicio"),
        fecha_fin=data.get("fecha_fin")
    )

    return jsonify(respuesta), codigo


# ==========================================
# CERRAR
# ==========================================

@jornada_bp.route(
    "/<int:id_jornada>/cerrar",
    methods=["PUT"]
)
def cerrar_jornada(id_jornada):

    respuesta, codigo = JornadaService.cerrar_jornada(
        id_jornada
    )

    return jsonify(respuesta), codigo


# ==========================================
# ELIMINAR
# ==========================================

@jornada_bp.route(
    "/<int:id_jornada>",
    methods=["DELETE"]
)
def eliminar_jornada(id_jornada):

    respuesta, codigo = JornadaService.eliminar_jornada(
        id_jornada
    )

    return jsonify(respuesta), codigo


# ==========================================
# REACTIVAR
# ==========================================

@jornada_bp.route(
    "/<int:id_jornada>/reactivar",
    methods=["PUT"]
)
def reactivar_jornada(id_jornada):

    respuesta, codigo = JornadaService.reactivar_jornada(
        id_jornada
    )

    return jsonify(respuesta), codigo