from flask import Blueprint, request, jsonify

from app.services.jornada_cajero_service import JornadaCajeroService


jornada_cajero_bp = Blueprint(
    "jornada_cajero",
    __name__,
    url_prefix="/api/jornadas"
)


# ASIGNAR
@jornada_cajero_bp.route(
    "/<int:id_jornada>/cajeros",
    methods=["POST"]
)
def asignar_cajeros(id_jornada):

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "No se enviaron datos."
        }), 400

    respuesta, codigo = JornadaCajeroService.asignar_cajeros(
        id_jornada=id_jornada,
        personas=data.get("personas")
    )

    return jsonify(respuesta), codigo


# LISTAR
@jornada_cajero_bp.route(
    "/<int:id_jornada>/cajeros",
    methods=["GET"]
)
def listar_cajeros(id_jornada):

    respuesta, codigo = JornadaCajeroService.listar_cajeros(
        id_jornada
    )

    return jsonify(respuesta), codigo


# QUITAR
@jornada_cajero_bp.route(
    "/<int:id_jornada>/cajeros/<int:id_persona>",
    methods=["DELETE"]
)
def quitar_cajero(id_jornada, id_persona):

    respuesta, codigo = JornadaCajeroService.quitar_cajero(
        id_jornada=id_jornada,
        id_persona=id_persona
    )

    return jsonify(respuesta), codigo