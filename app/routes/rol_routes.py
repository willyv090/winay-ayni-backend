from flask import Blueprint, request, jsonify
from app.services.rol_service import RolService


rol_bp = Blueprint(
    "rol",
    __name__,
    url_prefix="/api/roles"
)


# CREAR
@rol_bp.route("", methods=["POST"])
def crear_rol():

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "No se enviaron datos."
        }), 400

    respuesta, codigo = RolService.crear_rol(
        nombre=data.get("nombre"),
        descripcion=data.get("descripcion")
    )

    return jsonify(respuesta), codigo


# EDITAR
@rol_bp.route("/<int:id_rol>", methods=["PUT"])
def editar_rol(id_rol):

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "No se enviaron datos."
        }), 400

    respuesta, codigo = RolService.editar_rol(
        id_rol=id_rol,
        nombre=data.get("nombre"),
        descripcion=data.get("descripcion")
    )

    return jsonify(respuesta), codigo


# ELIMINAR
@rol_bp.route("/<int:id_rol>", methods=["DELETE"])
def eliminar_rol(id_rol):

    respuesta, codigo = RolService.eliminar_rol(
        id_rol
    )

    return jsonify(respuesta), codigo

#REACTIVAR
@rol_bp.route("/<int:id_rol>/reactivar", methods=["PUT"])
def reactivar_rol(id_rol):

    respuesta, codigo = RolService.reactivar_rol(id_rol)

    return jsonify(respuesta), codigo