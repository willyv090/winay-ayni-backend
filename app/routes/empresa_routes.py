from flask import Blueprint, request, jsonify
from app.services.empresa_service import EmpresaService


empresa_bp = Blueprint(
    "empresa",
    __name__,
    url_prefix="/api/empresas"
)


# CREAR
@empresa_bp.route("", methods=["POST"])
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
def listar_empresas():

    respuesta, codigo = EmpresaService.listar_empresas()

    return jsonify(respuesta), codigo


# EDITAR
@empresa_bp.route("/<int:id_empresa>", methods=["PUT"])
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
def reactivar_empresa(id_empresa):

    respuesta, codigo = EmpresaService.reactivar_empresa(
        id_empresa
    )

    return jsonify(respuesta), codigo