from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.venta_service import VentaService

venta_bp = Blueprint("venta", __name__, url_prefix="/api/ventas")


@venta_bp.route("", methods=["POST"])
@jwt_required()
def crear_venta():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not data:
        return jsonify({"error": "Se requiere un objeto JSON con los datos."}), 400
    respuesta, codigo = VentaService.crear_venta(
        id_jornada_cajero=data.get("id_jornada_cajero"),
        id_metodo_pago=data.get("id_metodo_pago"),
        tipo=data.get("tipo", "JORNADA"), fecha=data.get("fecha"),
        detalles=data.get("detalles"), id_persona=get_jwt_identity(),
        total_esperado=data.get("total_esperado")
    )
    return jsonify(respuesta), codigo


@venta_bp.route("", methods=["GET"])
@jwt_required()
def listar_ventas():
    respuesta, codigo = VentaService.listar_ventas(
        id_jornada=request.args.get("id_jornada"),
        id_persona=request.args.get("id_persona"),
        id_metodo_pago=request.args.get("id_metodo_pago"),
        id_empresa=request.args.get("id_empresa"), tipo=request.args.get("tipo"),
        usuario_id=get_jwt_identity(), rol=request.args.get("rol")
    )
    return jsonify(respuesta), codigo


@venta_bp.route("/<int:id_venta>", methods=["GET"])
@jwt_required()
def obtener_venta(id_venta):
    respuesta, codigo = VentaService.obtener_venta(
        id_venta, usuario_id=get_jwt_identity(), rol=request.args.get("rol")
    )
    return jsonify(respuesta), codigo


@venta_bp.route("/metricas/independientes", methods=["GET"])
@jwt_required()
def metricas_independientes():
    respuesta, codigo = VentaService.metricas_independientes(
        id_empresa=request.args.get("id_empresa"),
        usuario_id=get_jwt_identity(),
        desde=request.args.get("desde"),
        hasta=request.args.get("hasta")
    )
    return jsonify(respuesta), codigo


@venta_bp.route("/metricas/ferias", methods=["GET"])
@jwt_required()
def metricas_ferias():
    respuesta, codigo = VentaService.metricas_empresa(
        id_empresa=request.args.get("id_empresa"),
        usuario_id=get_jwt_identity(), desde=request.args.get("desde"),
        hasta=request.args.get("hasta"), tipo="JORNADA"
    )
    return jsonify(respuesta), codigo
