from app.extensions import db
from app.models.rol import Rol


class RolService:

    @staticmethod
    def crear_rol(nombre, descripcion):

        if not nombre:
            return {
                "error": "El nombre del rol es obligatorio."
            }, 400

        nombre = nombre.strip().upper()

        if descripcion:
            descripcion = descripcion.strip()

        rol_existente = Rol.query.filter_by(
            nombre=nombre
        ).first()

        if rol_existente:
            return {
                "error": "El rol ya se encuentra registrado."
            }, 409

        try:
            nuevo_rol = Rol(
                nombre=nombre,
                descripcion=descripcion,
                estado=True
            )

            db.session.add(nuevo_rol)
            db.session.commit()

            return {
                "mensaje": "Rol creado correctamente.",
                "rol": {
                    "id": nuevo_rol.id_rol,
                    "nombre": nuevo_rol.nombre,
                    "descripcion": nuevo_rol.descripcion,
                    "estado": nuevo_rol.estado
                }
            }, 201

        except Exception as e:
            db.session.rollback()

            return {
                "error": "No se pudo registrar el rol.",
                "detalle": str(e)
            }, 500

    # =========================
    # EDITAR ROL
    # =========================
    @staticmethod
    def editar_rol(id_rol, nombre, descripcion):

        rol = Rol.query.get(id_rol)

        if not rol:
            return {
                "error": "El rol no existe."
            }, 404

        if not nombre:
            return {
                "error": "El nombre del rol es obligatorio."
            }, 400

        nombre = nombre.strip().upper()

        if descripcion:
            descripcion = descripcion.strip()

        # Verificar que no exista otro rol con el mismo nombre
        rol_existente = Rol.query.filter(
            Rol.nombre == nombre,
            Rol.id_rol != id_rol
        ).first()

        if rol_existente:
            return {
                "error": "Ya existe otro rol con ese nombre."
            }, 409

        try:
            rol.nombre = nombre
            rol.descripcion = descripcion

            db.session.commit()

            return {
                "mensaje": "Rol actualizado correctamente.",
                "rol": {
                    "id": rol.id_rol,
                    "nombre": rol.nombre,
                    "descripcion": rol.descripcion,
                    "estado": rol.estado
                }
            }, 200

        except Exception as e:
            db.session.rollback()

            return {
                "error": "No se pudo actualizar el rol.",
                "detalle": str(e)
            }, 500

    # =========================
    # ELIMINAR ROL
    # =========================
    @staticmethod
    def eliminar_rol(id_rol):

        rol = Rol.query.get(id_rol)

        if not rol:
            return {
                "error": "El rol no existe."
            }, 404

        if not rol.estado:
            return {
                "error": "El rol ya se encuentra eliminado."
            }, 400

        try:
            # Eliminación lógica
            rol.estado = False

            db.session.commit()

            return {
                "mensaje": "Rol eliminado correctamente."
            }, 200

        except Exception as e:
            db.session.rollback()

            return {
                "error": "No se pudo eliminar el rol.",
                "detalle": str(e)
            }, 500

    @staticmethod
    def reactivar_rol(id_rol):

        rol = Rol.query.get(id_rol)

        if not rol:
            return {
                "error": "El rol no existe."
            }, 404

        if rol.estado:
            return {
                "error": "El rol ya se encuentra activo."
            }, 400

        try:
            rol.estado = True

            db.session.commit()

            return {
                "mensaje": "Rol reactivado correctamente.",
                "rol": {
                    "id": rol.id_rol,
                    "nombre": rol.nombre,
                    "estado": rol.estado
                }
            }, 200

        except Exception as e:
            db.session.rollback()

            return {
                "error": "No se pudo reactivar el rol.",
                "detalle": str(e)
            }, 500