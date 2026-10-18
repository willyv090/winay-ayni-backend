from flask import Blueprint, request, jsonify

from app.services.jornada_producto_service import JornadaProductoService


jornada_producto_bp = Blueprint(
    "jornada_producto",
    __name__,
    url_prefix="/api/jornadas"
)


# ASIGNAR
@jornada_producto_bp.route(
    "/<int:id_jornada>/empresas/<int:id_empresa>/productos",
    methods=["POST"]
)
def asignar_productos(id_jornada, id_empresa):

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "No se enviaron datos."
        }), 400

    respuesta, codigo = JornadaProductoService.asignar_productos(
        id_jornada=id_jornada,
        id_empresa=id_empresa,
        productos=data.get("productos")
    )

    return jsonify(respuesta), codigo


# LISTAR
@jornada_producto_bp.route(
    "/<int:id_jornada>/productos",
    methods=["GET"]
)
def listar_productos(id_jornada):

    respuesta, codigo = JornadaProductoService.listar_productos(
        id_jornada
    )

    return jsonify(respuesta), codigo


# QUITAR
@jornada_producto_bp.route(
    "/<int:id_jornada>/productos/<int:id_producto>",
    methods=["DELETE"]
)
def quitar_producto(id_jornada, id_producto):

    respuesta, codigo = JornadaProductoService.quitar_producto(
        id_jornada=id_jornada,
        id_producto=id_producto
    )

    return jsonify(respuesta), codigo

@jornada_producto_bp.route("/<int:id_jornada>/productos/caja", methods=["GET"])
def catalogo_caja(id_jornada):
    from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
    verify_jwt_in_request()
    respuesta, codigo = JornadaProductoService.catalogo_caja(id_jornada, get_jwt_identity())
    return jsonify(respuesta), codigo
