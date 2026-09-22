from datetime import date

from app.extensions import db
from app.models.jornada import Jornada
from app.models.persona import Persona
from app.models.jornada_cajero import JornadaCajero


class JornadaCajeroService:

    @staticmethod
    def asignar_cajeros(id_jornada, personas):

        jornada = Jornada.query.get(id_jornada)

        if not jornada:
            return {
                "error": "La jornada no existe."
            }, 404

        if not jornada.estado:
            return {
                "error": "No se pueden asignar cajeros a una jornada finalizada."
            }, 400

        if not isinstance(personas, list):
            return {
                "error": "El campo personas debe ser una lista."
            }, 400

        if len(personas) == 0:
            return {
                "error": "Debe seleccionar al menos una persona."
            }, 400

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
            return {
                "error": "Una o más personas no existen o están inactivas."
            }, 400

        try:

            relaciones = JornadaCajero.query.filter_by(
                jornada_id_jornada=id_jornada
            ).all()

            relaciones_por_persona = {
                relacion.persona_id_per: relacion
                for relacion in relaciones
            }

            for id_persona in personas:

                # Si ya existió, la reactivamos
                if id_persona in relaciones_por_persona:

                    relacion = relaciones_por_persona[id_persona]

                    relacion.estado = True
                    relacion.fecha = date.today()

                else:

                    nueva_relacion = JornadaCajero(
                        fecha=date.today(),
                        estado=True,
                        jornada_id_jornada=id_jornada,
                        persona_id_per=id_persona
                    )

                    db.session.add(nueva_relacion)

            db.session.commit()

            return {
                "mensaje": "Cajeros asignados correctamente."
            }, 200

        except Exception as e:

            db.session.rollback()

            return {
                "error": "No se pudieron asignar los cajeros.",
                "detalle": str(e)
            }, 500

    # ======================================
    # LISTAR CAJEROS
    # ======================================

    @staticmethod
    def listar_cajeros(id_jornada):

        jornada = Jornada.query.get(id_jornada)

        if not jornada:
            return {
                "error": "La jornada no existe."
            }, 404

        relaciones = JornadaCajero.query.filter_by(
            jornada_id_jornada=id_jornada
        ).order_by(
            JornadaCajero.id_jor_caj
        ).all()

        resultado = []

        for relacion in relaciones:

            resultado.append({
                "id_jornada_cajero": relacion.id_jor_caj,
                "fecha": relacion.fecha.isoformat(),
                "estado": relacion.estado,
                "persona": {
                    "id": relacion.persona.id_per,
                    "nombre": relacion.persona.nombre,
                    "usuario": relacion.persona.usuario
                }
            })

        return {
            "jornada": {
                "id": jornada.id_jornada,
                "nombre": jornada.nombre,
                "estado": jornada.estado
            },
            "cajeros": resultado
        }, 200

    # ======================================
    # QUITAR CAJERO
    # ======================================

    @staticmethod
    def quitar_cajero(id_jornada, id_persona):

        jornada = Jornada.query.get(id_jornada)

        if not jornada:
            return {
                "error": "La jornada no existe."
            }, 404

        if not jornada.estado:
            return {
                "error": "No se puede modificar una jornada finalizada."
            }, 400

        relacion = JornadaCajero.query.filter_by(
            jornada_id_jornada=id_jornada,
            persona_id_per=id_persona
        ).first()

        if not relacion:
            return {
                "error": "La persona no está asignada a esta jornada."
            }, 404

        if not relacion.estado:
            return {
                "error": "El cajero ya se encuentra desvinculado."
            }, 400

        try:

            relacion.estado = False

            db.session.commit()

            return {
                "mensaje": "Cajero retirado de la jornada correctamente."
            }, 200

        except Exception as e:

            db.session.rollback()

            return {
                "error": "No se pudo retirar el cajero.",
                "detalle": str(e)
            }, 500