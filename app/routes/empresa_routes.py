from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.permisos import solo_administrador
from app.services.empresa_service import EmpresaService


empresa_bp = Blueprint(
    "empresa",
    __name__,
    url_prefix="/api/empresas"
)


# CREAR
@empresa_bp.route("", methods=["POST"])
@solo_administrador
def crear_empresa():

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "No se enviaron datos."
        }), 400

    respuesta, codigo = EmpresaService.crear_empresa(
        nombre=data.get("nombre"),
        direccion=data.get("direccion"),
        telefono=data.get("telefono"),
        personas=data.get("personas", [])
    )

    return jsonify(respuesta), codigo


# LISTAR
@empresa_bp.route("", methods=["GET"])
@solo_administrador
def listar_empresas():

    respuesta, codigo = EmpresaService.listar_empresas()

    return jsonify(respuesta), codigo

# LISTAR POR ID
@empresa_bp.route("/<int:id_empresa>", methods=["GET"])
@solo_administrador
def obtener_empresa(id_empresa):

    respuesta, codigo = EmpresaService.obtener_empresa(
        id_empresa
    )

    return jsonify(respuesta), codigo

# EDITAR
@empresa_bp.route("/<int:id_empresa>", methods=["PUT"])
@solo_administrador
def editar_empresa(id_empresa):

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "No se enviaron datos."
        }), 400

    respuesta, codigo = EmpresaService.editar_empresa(
        id_empresa=id_empresa,
        nombre=data.get("nombre"),
        direccion=data.get("direccion"),
        telefono=data.get("telefono"),
        personas=data.get("personas")
    )

    return jsonify(respuesta), codigo


# ELIMINAR
@empresa_bp.route("/<int:id_empresa>", methods=["DELETE"])
@solo_administrador
def eliminar_empresa(id_empresa):

    respuesta, codigo = EmpresaService.eliminar_empresa(
        id_empresa
    )

    return jsonify(respuesta), codigo


# REACTIVAR
@empresa_bp.route(
    "/<int:id_empresa>/reactivar",
    methods=["PUT"]
)
@solo_administrador
def reactivar_empresa(id_empresa):

    respuesta, codigo = EmpresaService.reactivar_empresa(
        id_empresa
    )

    return jsonify(respuesta), codigo


# Consultas del emprendedor: identidad del JWT y vínculo activo.
@empresa_bp.route("/mias", methods=["GET"])
@jwt_required()
def listar_mis_empresas():
    respuesta, codigo = EmpresaService.listar_mias(get_jwt_identity())
    return jsonify(respuesta), codigo


@empresa_bp.route("/mias/<int:id_empresa>", methods=["GET"])
@jwt_required()
def obtener_mi_empresa(id_empresa):
    respuesta, codigo = EmpresaService.obtener_mia(get_jwt_identity(), id_empresa)
    return jsonify(respuesta), codigo
