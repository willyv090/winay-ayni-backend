from flask import Blueprint, request, jsonify

from app.services.persona_service import PersonaService


persona_bp = Blueprint(
    "persona",
    __name__,
    url_prefix="/api/personas"
)


@persona_bp.route("", methods=["POST"])
def crear_persona():

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "No se enviaron datos."
        }), 400

    respuesta, codigo = PersonaService.crear_persona(
        nombre=data.get("nombre"),
        usuario=data.get("usuario"),
        contrasenia=data.get("contrasenia"),
        id_rol=data.get("id_rol")
    )

    return jsonify(respuesta), codigo

@persona_bp.route("/<int:id_persona>", methods=["PUT"])
def editar_persona(id_persona):

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "No se enviaron datos."
        }), 400

    respuesta, codigo = PersonaService.editar_persona(
        id_persona=id_persona,
        nombre=data.get("nombre"),
        usuario=data.get("usuario"),
        contrasenia=data.get("contrasenia"),
        roles=data.get("roles")
    )

    return jsonify(respuesta), codigo


@persona_bp.route("/<int:id_persona>", methods=["DELETE"])
def eliminar_persona(id_persona):

    respuesta, codigo = PersonaService.eliminar_persona(
        id_persona
    )

    return jsonify(respuesta), codigo

@persona_bp.route("/<int:id_persona>/reactivar", methods=["PUT"])
def reactivar_persona(id_persona):

    respuesta, codigo = PersonaService.reactivar_persona(
        id_persona
    )

    return jsonify(respuesta), codigo