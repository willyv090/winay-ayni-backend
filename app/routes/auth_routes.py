from flask import Blueprint, request, jsonify
from app.services.auth_service import AuthService


auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/api/auth"
)


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    if not data:
        return jsonify({
            "error": "No se enviaron datos."
        }), 400

    usuario = data.get("usuario")
    contrasenia = data.get("contrasenia")

    if not usuario or not contrasenia:
        return jsonify({
            "error": "Usuario y contraseña son obligatorios."
        }), 400

    respuesta, codigo = AuthService.login(
        usuario=usuario,
        contrasenia=contrasenia
    )

    return jsonify(respuesta), codigo