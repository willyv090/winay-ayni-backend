from werkzeug.security import check_password_hash
from flask_jwt_extended import create_access_token

from app.models import Persona, RolPersona, Rol


class AuthService:

    @staticmethod
    def login(usuario, contrasenia):

        # Buscar persona por usuario
        persona = Persona.query.filter_by(
            usuario=usuario
        ).first()

        # Si no existe el usuario
        if not persona:
            return {
                "error": "Usuario o contraseña incorrectos."
            }, 401

        # Verificar que la persona esté activa
        if not persona.estado:
            return {
                "error": "El usuario se encuentra inactivo."
            }, 403

        # Verificar contraseña
        if not check_password_hash(
            persona.contrasenia,
            contrasenia
        ):
            return {
                "error": "Usuario o contraseña incorrectos."
            }, 401

        # Buscar roles activos de la persona
        roles_persona = RolPersona.query.filter_by(
            persona_id_per=persona.id_per,
            estado=True
        ).all()

        roles = []

        for rol_persona in roles_persona:

            rol = Rol.query.filter_by(
                id_rol=rol_persona.rol_id_rol,
                estado=True
            ).first()

            if rol:
                roles.append(rol.nombre)

        # Crear JWT
        token = create_access_token(
            identity=str(persona.id_per),
            additional_claims={
                "usuario": persona.usuario,
                "roles": roles
            }
        )

        return {
            "mensaje": "Inicio de sesión correcto.",
            "token": token,
            "usuario": {
                "id": persona.id_per,
                "nombre": persona.nombre,
                "usuario": persona.usuario,
                "roles": roles
            }
        }, 200