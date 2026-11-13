from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.venta_service import VentaError, VentaService


def validar_administrador():
    try:
        VentaService.contexto(get_jwt_identity(), "ADMINISTRADOR")
    except VentaError as error:
        return jsonify({"error": error.mensaje}), error.codigo
    return None


def solo_administrador(vista):
    @wraps(vista)
    @jwt_required()
    def protegida(*args, **kwargs):
        rechazo = validar_administrador()
        if rechazo is not None:
            return rechazo
        return vista(*args, **kwargs)

    return protegida
