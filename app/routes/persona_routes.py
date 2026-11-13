from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.permisos import solo_administrador, validar_administrador
from app.services.persona_service import PersonaService


persona_bp = Blueprint(
    "persona",
    __name__,
    url_prefix="/api/personas"
)

@persona_bp.route("", methods=["GET"])
@solo_administrador
def listar_personas():

    respuesta, codigo = PersonaService.listar_personas()

    return jsonify(respuesta), codigo

@persona_bp.route("", methods=["POST"])
@solo_administrador
def crear_persona():

    data = request.get_json() or {}

    if not data:
        return jsonify({
            "error": "No se enviaron datos."
        }), 400

    respuesta, codigo = PersonaService.crear_persona(
        nombre=data.get("nombre"),
        usuario=data.get("usuario"),
        contrasenia=data.get("contrasenia"),
        roles=data.get("roles", [])
    )

    return jsonify(respuesta), codigo

@persona_bp.route("/<int:id_persona>", methods=["PUT"])
@solo_administrador
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
@solo_administrador
def eliminar_persona(id_persona):

    respuesta, codigo = PersonaService.eliminar_persona(
        id_persona
    )

    return jsonify(respuesta), codigo

@persona_bp.route("/<int:id_persona>/reactivar", methods=["PUT"])
@solo_administrador
def reactivar_persona(id_persona):

    respuesta, codigo = PersonaService.reactivar_persona(
        id_persona
    )

    return jsonify(respuesta), codigo

@persona_bp.route("/<int:id_persona>", methods=["GET"])
@jwt_required()
def obtener_persona(id_persona):
    # Inicio consulta el perfil propio para actualizar los roles de la sesión.
    if str(id_persona) != str(get_jwt_identity()):
        rechazo = validar_administrador()
        if rechazo is not None:
            return rechazo


    respuesta, codigo = PersonaService.obtener_persona(
        id_persona
    )

    return jsonify(respuesta), codigo