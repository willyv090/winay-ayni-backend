from werkzeug.security import generate_password_hash

from app import db
from app.models.persona import Persona
from app.models.rol import Rol
from app.models.rol_persona import RolPersona


class PersonaService:

    @staticmethod
    def crear_persona(nombre, usuario, contrasenia, id_rol):

        # Validar datos obligatorios
        if not nombre or not usuario or not contrasenia or not id_rol:
            return {
                "error": "Todos los campos son obligatorios."
            }, 400

        # Limpiar datos
        nombre = nombre.strip()
        usuario = usuario.strip()

        # Verificar si ya existe el usuario
        persona_existente = Persona.query.filter_by(
            usuario=usuario
        ).first()

        if persona_existente:
            return {
                "error": "El usuario ya se encuentra registrado."
            }, 409

        # Verificar que el rol exista y esté activo
        rol = Rol.query.filter_by(
            id_rol=id_rol,
            estado=True
        ).first()

        if not rol:
            return {
                "error": "El rol seleccionado no existe o se encuentra inactivo."
            }, 404

        try:

            # Generar HASH de la contraseña
            contrasenia_hash = generate_password_hash(contrasenia)

            # Crear persona
            nueva_persona = Persona(
                nombre=nombre,
                usuario=usuario,
                contrasenia=contrasenia_hash,
                estado=True
            )

            db.session.add(nueva_persona)

            # Ejecutar INSERT sin hacer COMMIT todavía.
            # Esto nos permite obtener id_per.
            db.session.flush()

            # Relacionar persona con rol
            nuevo_rol_persona = RolPersona(
                persona_id_per=nueva_persona.id_per,
                rol_id_rol=rol.id_rol,
                estado=True
            )

            db.session.add(nuevo_rol_persona)

            # Ahora sí guardar ambas operaciones
            db.session.commit()

            return {
                "mensaje": "Persona creada correctamente.",
                "persona": {
                    "id": nueva_persona.id_per,
                    "nombre": nueva_persona.nombre,
                    "usuario": nueva_persona.usuario,
                    "rol": rol.nombre
                }
            }, 201

        except Exception as e:

            db.session.rollback()

            return {
                "error": "No se pudo registrar la persona.",
                "detalle": str(e)
            }, 500

    @staticmethod
    def editar_persona(
        id_persona,
        nombre,
        usuario,
        contrasenia=None,
        roles=None
    ):

        persona = Persona.query.get(id_persona)

        if not persona:
            return {
                "error": "La persona no existe."
            }, 404

        if not persona.estado:
            return {
                "error": "No se puede modificar una persona inactiva."
            }, 400

        if not nombre or not usuario:
            return {
                "error": "Nombre y usuario son obligatorios."
            }, 400

        nombre = nombre.strip()
        usuario = usuario.strip()

        # Verificar que otro usuario no tenga el mismo nombre de usuario
        persona_existente = Persona.query.filter(
            Persona.usuario == usuario,
            Persona.id_per != id_persona
        ).first()

        if persona_existente:
            return {
                "error": "El usuario ya se encuentra registrado."
            }, 409

        try:

            # Actualizar datos de persona
            persona.nombre = nombre
            persona.usuario = usuario

            # Cambiar contraseña solo si se envió una nueva
            if contrasenia:
                persona.contrasenia = generate_password_hash(
                    contrasenia
                )

            # ==========================
            # ACTUALIZAR ROLES
            # ==========================
            if roles is not None:

                # Eliminar IDs repetidos
                roles = list(set(roles))

                if len(roles) == 0:
                    return {
                        "error": "La persona debe tener al menos un rol."
                    }, 400

                # Verificar que todos los roles existan y estén activos
                roles_validos = Rol.query.filter(
                    Rol.id_rol.in_(roles),
                    Rol.estado == True
                ).all()

                ids_roles_validos = {
                    rol.id_rol for rol in roles_validos
                }

                if ids_roles_validos != set(roles):
                    return {
                        "error": "Uno o más roles no existen o están inactivos."
                    }, 400

                # Obtener todas las relaciones que alguna vez tuvo la persona
                relaciones = RolPersona.query.filter_by(
                    persona_id_per=id_persona
                ).all()

                relaciones_por_rol = {
                    relacion.rol_id_rol: relacion
                    for relacion in relaciones
                }

                # Activar los recibidos y desactivar los que ya no vienen
                for relacion in relaciones:

                    if relacion.rol_id_rol in roles:
                        relacion.estado = True
                    else:
                        relacion.estado = False

                # Crear relaciones nuevas
                for id_rol in roles:

                    if id_rol not in relaciones_por_rol:

                        nueva_relacion = RolPersona(
                            persona_id_per=id_persona,
                            rol_id_rol=id_rol,
                            estado=True
                        )

                        db.session.add(nueva_relacion)

            db.session.commit()

            return {
                "mensaje": "Persona actualizada correctamente.",
                "persona": {
                    "id": persona.id_per,
                    "nombre": persona.nombre,
                    "usuario": persona.usuario,
                    "estado": persona.estado,
                    "roles": roles
                }
            }, 200

        except Exception as e:

            db.session.rollback()

            return {
                "error": "No se pudo actualizar la persona.",
                "detalle": str(e)
            }, 500

    @staticmethod
    def eliminar_persona(id_persona):

        persona = Persona.query.get(id_persona)

        if not persona:
            return {
                "error": "La persona no existe."
            }, 404

        if not persona.estado:
            return {
                "error": "La persona ya se encuentra inactiva."
            }, 400

        try:
            # Eliminación lógica
            persona.estado = False

            # Desactivar también sus relaciones de rol
            roles_persona = RolPersona.query.filter_by(
                persona_id_per=id_persona,
                estado=True
            ).all()

            for rol_persona in roles_persona:
                rol_persona.estado = False

            db.session.commit()

            return {
                "mensaje": "Persona eliminada correctamente."
            }, 200

        except Exception as e:

            db.session.rollback()

            return {
                "error": "No se pudo eliminar la persona.",
                "detalle": str(e)
            }, 500

    @staticmethod
    def reactivar_persona(id_persona):

        persona = Persona.query.get(id_persona)

        if not persona:
            return {
                "error": "La persona no existe."
            }, 404

        if persona.estado:
            return {
                "error": "La persona ya se encuentra activa."
            }, 400

        try:
            persona.estado = True

            db.session.commit()

            return {
                "mensaje": "Persona reactivada correctamente.",
                "persona": {
                    "id": persona.id_per,
                    "nombre": persona.nombre,
                    "usuario": persona.usuario,
                    "estado": persona.estado
                }
            }, 200

        except Exception as e:
            db.session.rollback()

            return {
                "error": "No se pudo reactivar la persona.",
                "detalle": str(e)
            }, 500