from werkzeug.security import generate_password_hash

from app import db
from app.models.persona import Persona
from app.models.rol import Rol
from app.models.rol_persona import RolPersona
from app.models.empresa import Empresa
from app.models.persona_empresa import PersonaEmpresa

class PersonaService:

    @staticmethod
    def listar_personas():
        try:

            personas = Persona.query.order_by(
                Persona.id_per.asc()
            ).all()

            resultado = []

            for persona in personas:

                roles_query = (
                    Rol.query
                    .join(
                        RolPersona,
                        Rol.id_rol == RolPersona.rol_id_rol
                    )
                    .filter(
                        RolPersona.persona_id_per == persona.id_per,
                        RolPersona.estado == True,
                        Rol.estado == True
                    )
                    .all()
                )

                roles = [
                    rol.nombre
                    for rol in roles_query
                ]

                resultado.append({
                    "id": persona.id_per,
                    "nombre": persona.nombre,
                    "usuario": persona.usuario,
                    "estado": persona.estado,
                    "roles": roles
                })

            return {
                "personas": resultado
            }, 200

        except Exception as error:

            print(f"Error al listar personas: {error}")

            return {
                "error": "No se pudieron obtener los usuarios."
            }, 500

    @staticmethod
    def crear_persona(nombre, usuario, contrasenia, roles):

        # Validar datos obligatorios
        if not nombre or not usuario or not contrasenia:
            return {
                "error": "Nombre, usuario y contraseña son obligatorios."
            }, 400

        if not roles:
            return {
                "error": "Debe seleccionar al menos un rol."
            }, 400

        if not isinstance(roles, list):
            return {
                "error": "Los roles deben enviarse como una lista."
            }, 400

        # Limpiar datos
        nombre = nombre.strip()
        usuario = usuario.strip()

        # Evitar roles repetidos
        roles = list(set(roles))

        # Verificar si ya existe el usuario
        persona_existente = Persona.query.filter_by(
            usuario=usuario
        ).first()

        if persona_existente:
            return {
                "error": "El usuario ya se encuentra registrado."
            }, 409

        # Verificar que todos los roles existan y estén activos
        roles_encontrados = (
            Rol.query
            .filter(
                Rol.id_rol.in_(roles),
                Rol.estado == True
            )
            .all()
        )

        if len(roles_encontrados) != len(roles):
            return {
                "error": "Uno o más roles seleccionados no existen o se encuentran inactivos."
            }, 404

        try:

            # Generar HASH de la contraseña
            contrasenia_hash = generate_password_hash(
                contrasenia
            )

            # Crear persona
            nueva_persona = Persona(
                nombre=nombre,
                usuario=usuario,
                contrasenia=contrasenia_hash,
                estado=True
            )

            db.session.add(nueva_persona)

            # Obtener id_per antes del commit
            db.session.flush()

            # Relacionar persona con todos sus roles
            for rol in roles_encontrados:

                nuevo_rol_persona = RolPersona(
                    persona_id_per=nueva_persona.id_per,
                    rol_id_rol=rol.id_rol,
                    estado=True
                )

                db.session.add(nuevo_rol_persona)

            # Guardar persona + relaciones
            db.session.commit()

            return {
                "mensaje": "Persona creada correctamente.",
                "persona": {
                    "id": nueva_persona.id_per,
                    "nombre": nueva_persona.nombre,
                    "usuario": nueva_persona.usuario,
                    "estado": nueva_persona.estado,
                    "roles": [
                        rol.nombre
                        for rol in roles_encontrados
                    ]
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

    @staticmethod
    def obtener_persona(id_persona):
        try:
            persona = Persona.query.get(id_persona)

            if not persona:
                return {
                    "error": "Usuario no encontrado."
                }, 404

            # =========================
            # ROLES ACTIVOS
            # =========================
            roles_query = (
                Rol.query
                .join(
                    RolPersona,
                    Rol.id_rol == RolPersona.rol_id_rol
                )
                .filter(
                    RolPersona.persona_id_per == persona.id_per,
                    RolPersona.estado == True,
                    Rol.estado == True
                )
                .all()
            )

            roles = [
                rol.nombre
                for rol in roles_query
            ]

            # =========================
            # EMPRESAS ASOCIADAS ACTIVAS
            # =========================
            empresas_query = (
                Empresa.query
                .join(
                    PersonaEmpresa,
                    Empresa.id_empresa ==
                    PersonaEmpresa.empresa_id_empresa
                )
                .filter(
                    PersonaEmpresa.persona_id_per == persona.id_per,
                    PersonaEmpresa.estado == True,
                    Empresa.estado == True
                )
                .all()
            )

            empresas = [
                {
                    "id": empresa.id_empresa,
                    "nombre": empresa.nombre,
                    "direccion": empresa.direccion,
                    "telefono": empresa.telefono
                }
                for empresa in empresas_query
            ]

            return {
                "persona": {
                    "id": persona.id_per,
                    "nombre": persona.nombre,
                    "usuario": persona.usuario,
                    "estado": persona.estado,
                    "roles": roles,
                    "empresas": empresas
                }
            }, 200

        except Exception as error:
            print(f"Error al obtener persona: {error}")

            return {
                "error": "No se pudo obtener el usuario."
            }, 500