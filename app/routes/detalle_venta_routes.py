from flask import Blueprint, request, jsonify

from app.services.detalle_venta_service import DetalleVentaService


detalle_venta_bp = Blueprint(
    "detalle_venta",
    __name__,
    url_prefix="/api/ventas"
)


# ==========================================
# AGREGAR PRODUCTO
# ==========================================

@detalle_venta_bp.route(
    "/<int:id_venta>/detalles",
    methods=["POST"]
)
def agregar_detalles(id_venta):

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "No se enviaron datos."
        }), 400

    respuesta, codigo = DetalleVentaService.agregar_detalles(
        id_venta=id_venta,
        detalles=data.get("detalles")
    )

    return jsonify(respuesta), codigo


# ==========================================
# LISTAR DETALLES
# ==========================================

@detalle_venta_bp.route(
    "/<int:id_venta>/detalles",
    methods=["GET"]
)
def listar_detalles(id_venta):

    respuesta, codigo = DetalleVentaService.listar_detalles(
        id_venta
    )

    return jsonify(respuesta), codigo


# ==========================================
# MODIFICAR CANTIDAD
# ==========================================

@detalle_venta_bp.route(
    "/<int:id_venta>/detalles/<int:id_detalle>",
    methods=["PUT"]
)
def editar_cantidad(id_venta, id_detalle):

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "No se enviaron datos."
        }), 400

    respuesta, codigo = DetalleVentaService.editar_cantidad(
        id_venta=id_venta,
        id_detalle=id_detalle,
        cantidad=data.get("cantidad")
    )

    return jsonify(respuesta), codigo


# ==========================================
# QUITAR PRODUCTO
# ==========================================

@detalle_venta_bp.route(
    "/<int:id_venta>/detalles/<int:id_detalle>",
    methods=["DELETE"]
)
def eliminar_detalle(id_venta, id_detalle):

    respuesta, codigo = DetalleVentaService.eliminar_detalle(
        id_venta=id_venta,
        id_detalle=id_detalle
    )

    return jsonify(respuesta), codigo