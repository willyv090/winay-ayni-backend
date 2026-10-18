from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.detalle_venta_service import DetalleVentaService

detalle_venta_bp = Blueprint("detalle_venta", __name__, url_prefix="/api/ventas")


@detalle_venta_bp.route("/<int:id_venta>/detalles", methods=["POST"])
@jwt_required()
def agregar_detalles(id_venta):
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not data:
        return jsonify({"error": "Se requiere un objeto JSON con los datos."}), 400
    respuesta, codigo = DetalleVentaService.agregar_detalles(
        id_venta, data.get("detalles"), id_persona=get_jwt_identity()
    )
    return jsonify(respuesta), codigo


@detalle_venta_bp.route("/<int:id_venta>/detalles", methods=["GET"])
@jwt_required()
def listar_detalles(id_venta):
    respuesta, codigo = DetalleVentaService.listar_detalles(
        id_venta, usuario_id=get_jwt_identity(), rol=request.args.get("rol"), id_empresa=request.args.get("id_empresa")
    )
    return jsonify(respuesta), codigo


@detalle_venta_bp.route("/<int:id_venta>/detalles/<int:id_detalle>", methods=["PUT"])
@jwt_required()
def editar_cantidad(id_venta, id_detalle):
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not data:
        return jsonify({"error": "Se requiere un objeto JSON con los datos."}), 400
    respuesta, codigo = DetalleVentaService.editar_cantidad(
        id_venta, id_detalle, data.get("cantidad"), id_persona=get_jwt_identity()
    )
    return jsonify(respuesta), codigo


@detalle_venta_bp.route("/<int:id_venta>/detalles/<int:id_detalle>", methods=["DELETE"])
@jwt_required()
def eliminar_detalle(id_venta, id_detalle):
    respuesta, codigo = DetalleVentaService.eliminar_detalle(
        id_venta, id_detalle, id_persona=get_jwt_identity()
    )
    return jsonify(respuesta), codigo
