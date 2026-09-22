from app.extensions import db
from app.models.empresa import Empresa
from app.models.persona import Persona
from app.models.persona_empresa import PersonaEmpresa


class EmpresaService:

    @staticmethod
    def crear_empresa(nombre, direccion, telefono, personas=None):

        if not nombre:
            return {
                "error": "El nombre de la empresa es obligatorio."
            }, 400

        if not telefono:
            return {
                "error": "El teléfono es obligatorio."
            }, 400

        if personas is not None and not isinstance(personas, list):
            return {
                "error": "El campo personas debe ser una lista."
            }, 400

        nombre = nombre.strip()

        if direccion:
            direccion = direccion.strip()

        empresa_existente = Empresa.query.filter(
            db.func.lower(Empresa.nombre) == nombre.lower()
        ).first()

        if empresa_existente:
            return {
                "error": "La empresa ya se encuentra registrada."
            }, 409

        try:
            nueva_empresa = Empresa(
                nombre=nombre,
                direccion=direccion,
                telefono=telefono,
                estado=True
            )

            db.session.add(nueva_empresa)
            db.session.flush()

            if personas:
                personas = list(set(personas))

                personas_validas = Persona.query.filter(
                    Persona.id_per.in_(personas),
                    Persona.estado == True
                ).all()

                ids_validos = {
                    persona.id_per
                    for persona in personas_validas
                }

                if ids_validos != set(personas):
                    db.session.rollback()

                    return {
                        "error": "Una o más personas no existen o están inactivas."
                    }, 400

                for id_persona in personas:
                    relacion = PersonaEmpresa(
                        persona_id_per=id_persona,
                        empresa_id_empresa=nueva_empresa.id_empresa,
                        estado=True
                    )

                    db.session.add(relacion)

            db.session.commit()

            return {
                "mensaje": "Empresa creada correctamente.",
                "empresa": {
                    "id": nueva_empresa.id_empresa,
                    "nombre": nueva_empresa.nombre,
                    "direccion": nueva_empresa.direccion,
                    "telefono": nueva_empresa.telefono,
                    "estado": nueva_empresa.estado
                }
            }, 201

        except Exception as e:
            db.session.rollback()

            return {
                "error": "No se pudo registrar la empresa.",
                "detalle": str(e)
            }, 500

    # ==========================
    # LISTAR
    # ==========================
    @staticmethod
    def listar_empresas():

        empresas = Empresa.query.order_by(
            Empresa.id_empresa
        ).all()

        resultado = []

        for empresa in empresas:

            relaciones = PersonaEmpresa.query.filter_by(
                empresa_id_empresa=empresa.id_empresa,
                estado=True
            ).all()

            personas = []

            for relacion in relaciones:

                persona = Persona.query.get(
                    relacion.persona_id_per
                )

                if persona and persona.estado:
                    personas.append({
                        "id": persona.id_per,
                        "nombre": persona.nombre,
                        "usuario": persona.usuario
                    })

            resultado.append({
                "id": empresa.id_empresa,
                "nombre": empresa.nombre,
                "direccion": empresa.direccion,
                "telefono": empresa.telefono,
                "estado": empresa.estado,
                "personas": personas
            })

        return {
            "empresas": resultado
        }, 200

    # ==========================
    # EDITAR
    # ==========================
    @staticmethod
    def editar_empresa(
        id_empresa,
        nombre,
        direccion,
        telefono,
        personas=None
    ):

        empresa = Empresa.query.get(id_empresa)

        if not empresa:
            return {
                "error": "La empresa no existe."
            }, 404

        if not empresa.estado:
            return {
                "error": "No se puede modificar una empresa inactiva."
            }, 400

        if not nombre:
            return {
                "error": "El nombre de la empresa es obligatorio."
            }, 400

        if not telefono:
            return {
                "error": "El teléfono es obligatorio."
            }, 400

        if personas is not None and not isinstance(personas, list):
            return {
                "error": "El campo personas debe ser una lista."
            }, 400

        nombre = nombre.strip()

        if direccion:
            direccion = direccion.strip()

        empresa_existente = Empresa.query.filter(
            db.func.lower(Empresa.nombre) == nombre.lower(),
            Empresa.id_empresa != id_empresa
        ).first()

        if empresa_existente:
            return {
                "error": "Ya existe otra empresa con ese nombre."
            }, 409

        try:

            empresa.nombre = nombre
            empresa.direccion = direccion
            empresa.telefono = telefono

            # =============================
            # ACTUALIZAR PERSONAS
            # =============================
            if personas is not None:

                personas = list(set(personas))

                # Validar personas recibidas
                if personas:

                    personas_validas = Persona.query.filter(
                        Persona.id_per.in_(personas),
                        Persona.estado == True
                    ).all()

                    ids_validos = {
                        persona.id_per
                        for persona in personas_validas
                    }

                    if ids_validos != set(personas):
                        db.session.rollback()

                        return {
                            "error": "Una o más personas no existen o están inactivas."
                        }, 400

                # Obtener todas las relaciones existentes
                relaciones = PersonaEmpresa.query.filter_by(
                    empresa_id_empresa=id_empresa
                ).all()

                relaciones_por_persona = {
                    relacion.persona_id_per: relacion
                    for relacion in relaciones
                }

                # Activar o desactivar relaciones existentes
                for relacion in relaciones:

                    if relacion.persona_id_per in personas:
                        relacion.estado = True
                    else:
                        relacion.estado = False

                # Crear relaciones que nunca existieron
                for id_persona in personas:

                    if id_persona not in relaciones_por_persona:

                        nueva_relacion = PersonaEmpresa(
                            persona_id_per=id_persona,
                            empresa_id_empresa=id_empresa,
                            estado=True
                        )

                        db.session.add(nueva_relacion)

            db.session.commit()

            return {
                "mensaje": "Empresa actualizada correctamente.",
                "empresa": {
                    "id": empresa.id_empresa,
                    "nombre": empresa.nombre,
                    "direccion": empresa.direccion,
                    "telefono": empresa.telefono,
                    "estado": empresa.estado,
                    "personas": personas
                }
            }, 200

        except Exception as e:

            db.session.rollback()

            return {
                "error": "No se pudo actualizar la empresa.",
                "detalle": str(e)
            }, 500

    # ==========================
    # ELIMINAR LÓGICAMENTE
    # ==========================
    @staticmethod
    def eliminar_empresa(id_empresa):

        empresa = Empresa.query.get(id_empresa)

        if not empresa:
            return {
                "error": "La empresa no existe."
            }, 404

        if not empresa.estado:
            return {
                "error": "La empresa ya se encuentra inactiva."
            }, 400

        try:

            empresa.estado = False

            db.session.commit()

            return {
                "mensaje": "Empresa eliminada correctamente."
            }, 200

        except Exception as e:

            db.session.rollback()

            return {
                "error": "No se pudo eliminar la empresa.",
                "detalle": str(e)
            }, 500

    # ==========================
    # REACTIVAR
    # ==========================
    @staticmethod
    def reactivar_empresa(id_empresa):

        empresa = Empresa.query.get(id_empresa)

        if not empresa:
            return {
                "error": "La empresa no existe."
            }, 404

        if empresa.estado:
            return {
                "error": "La empresa ya se encuentra activa."
            }, 400

        try:

            empresa.estado = True

            db.session.commit()

            return {
                "mensaje": "Empresa reactivada correctamente.",
                "empresa": {
                    "id": empresa.id_empresa,
                    "nombre": empresa.nombre,
                    "estado": empresa.estado
                }
            }, 200

        except Exception as e:

            db.session.rollback()

            return {
                "error": "No se pudo reactivar la empresa.",
                "detalle": str(e)
            }, 500