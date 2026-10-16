from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity

from app.services.producto_service import ProductoService


producto_bp = Blueprint(
    "producto",
    __name__,
    url_prefix="/api/productos"
)


@producto_bp.before_request
def validar_acceso_productos():
    if request.method == "OPTIONS":
        return None
    verify_jwt_in_request()
    escritura = request.method != "GET"
    datos = request.get_json(silent=True) if escritura else None
    if request.method == "POST" or request.endpoint in (
        "producto.editar_producto", "producto.ajustar_stock"
    ):
        if not isinstance(datos, dict) or not datos:
            return jsonify({"error": "Se requiere un objeto JSON con los datos."}), 400
    argumentos = request.view_args or {}
    id_empresa = argumentos.get("id_empresa")
    if request.endpoint in ("producto.crear_producto", "producto.editar_producto"):
        id_empresa = datos.get("id_empresa")
    respuesta, codigo, restringido = ProductoService.autorizar(
        get_jwt_identity(), escritura=escritura,
        propio=request.args.get("ambito") == "propio",
        id_empresa=id_empresa, id_producto=argumentos.get("id_producto")
    )
    if respuesta is not None:
        return jsonify(respuesta), codigo
    g.productos_persona = get_jwt_identity() if restringido else None


# ==========================================
# CREAR
# ==========================================

@producto_bp.route("", methods=["POST"])
def crear_producto():

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "No se enviaron datos."
        }), 400

    respuesta, codigo = ProductoService.crear_producto(
        nombre=data.get("nombre"),
        cantidad=data.get("cantidad"),
        precio_u=data.get("precio_u"),
        rebaja=data.get("rebaja"),
        fecha_ingreso=data.get("fecha_ingreso"),
        fecha_salida=data.get("fecha_salida"),
        notas=data.get("notas"),
        id_empresa=data.get("id_empresa")
    )

    return jsonify(respuesta), codigo


# ==========================================
# LISTAR
# ==========================================

@producto_bp.route("", methods=["GET"])
def listar_productos():

    respuesta, codigo = ProductoService.listar_productos(g.productos_persona)

    return jsonify(respuesta), codigo


# ==========================================
# OBTENER UNO
# ==========================================

@producto_bp.route("/<int:id_producto>", methods=["GET"])
def obtener_producto(id_producto):

    respuesta, codigo = ProductoService.obtener_producto(
        id_producto
    )

    return jsonify(respuesta), codigo

#==========================================
# OBTERNER POR EMPRESA Y FILTRAR POR NOMBRE
#==========================================
@producto_bp.route(
    "/empresa/<int:id_empresa>",
    methods=["GET"]
)
def listar_productos_empresa(id_empresa):

    buscar = request.args.get("buscar")

    respuesta, codigo = ProductoService.listar_productos_empresa(
        id_empresa=id_empresa,
        buscar=buscar,
        estado=request.args.get('estado', 'activos')
    )

    return jsonify(respuesta), codigo

# ==========================================
# EDITAR
# ==========================================

@producto_bp.route("/<int:id_producto>", methods=["PUT"])
def editar_producto(id_producto):

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "No se enviaron datos."
        }), 400

    respuesta, codigo = ProductoService.editar_producto(
        id_producto=id_producto,
        nombre=data.get("nombre"),
        precio_u=data.get("precio_u"),
        rebaja=data.get("rebaja"),
        fecha_ingreso=data.get("fecha_ingreso"),
        fecha_salida=data.get("fecha_salida"),
        notas=data.get("notas"),
        id_empresa=data.get("id_empresa")
    )

    return jsonify(respuesta), codigo


# ==========================================
# ELIMINAR
# ==========================================

@producto_bp.route("/<int:id_producto>", methods=["DELETE"])
def eliminar_producto(id_producto):

    respuesta, codigo = ProductoService.eliminar_producto(
        id_producto
    )

    return jsonify(respuesta), codigo


# ==========================================
# REACTIVAR
# ==========================================

@producto_bp.route(
    "/<int:id_producto>/reactivar",
    methods=["PUT"]
)
def reactivar_producto(id_producto):

    respuesta, codigo = ProductoService.reactivar_producto(
        id_producto
    )

    return jsonify(respuesta), codigo


# ==========================================
# AJUSTAR INVENTARIO
# ==========================================

@producto_bp.route(
    "/<int:id_producto>/stock",
    methods=["PUT"]
)
def ajustar_stock(id_producto):

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "No se enviaron datos."
        }), 400

    respuesta, codigo = ProductoService.ajustar_stock(
        id_producto=id_producto,
        ajuste=data.get("ajuste"),
        notas=data.get("notas")
    )

    return jsonify(respuesta), codigo