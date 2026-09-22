from datetime import date

from app.extensions import db
from app.models.jornada import Jornada


class JornadaService:

    # ==========================================
    # MÉTODOS AUXILIARES
    # ==========================================

    @staticmethod
    def _convertir_fecha(valor, nombre_campo):

        if not valor:
            raise ValueError(
                f"El campo {nombre_campo} es obligatorio."
            )

        if isinstance(valor, date):
            return valor

        try:
            return date.fromisoformat(valor)

        except (TypeError, ValueError):
            raise ValueError(
                f"El campo {nombre_campo} debe tener formato YYYY-MM-DD."
            )

    @staticmethod
    def _jornada_json(jornada):

        return {
            "id": jornada.id_jornada,
            "nombre": jornada.nombre,
            "direccion": jornada.direccion,
            "fecha_inicio": jornada.fecha_inicio.isoformat(),
            "fecha_fin": jornada.fecha_fin.isoformat(),
            "estado": jornada.estado,
        }

    # ==========================================
    # CREAR / ABRIR JORNADA
    # ==========================================

    @staticmethod
    def crear_jornada(
        nombre,
        direccion,
        fecha_inicio,
        fecha_fin
    ):

        if not nombre:
            return {
                "error": "El nombre de la jornada es obligatorio."
            }, 400

        if not direccion:
            return {
                "error": "La dirección es obligatoria."
            }, 400

        try:

            fecha_inicio = JornadaService._convertir_fecha(
                fecha_inicio,
                "fecha_inicio"
            )

            fecha_fin = JornadaService._convertir_fecha(
                fecha_fin,
                "fecha_fin"
            )

        except ValueError as e:
            return {
                "error": str(e)
            }, 400

        if fecha_fin < fecha_inicio:
            return {
                "error": "La fecha de fin no puede ser anterior a la fecha de inicio."
            }, 400

        try:

            nueva_jornada = Jornada(
                nombre=nombre.strip(),
                direccion=direccion.strip(),
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                estado=True,
            )

            db.session.add(nueva_jornada)
            db.session.commit()

            return {
                "mensaje": "Jornada creada correctamente.",
                "jornada": JornadaService._jornada_json(
                    nueva_jornada
                )
            }, 201

        except Exception as e:

            db.session.rollback()

            return {
                "error": "No se pudo crear la jornada.",
                "detalle": str(e)
            }, 500

    # ==========================================
    # LISTAR
    # ==========================================

    @staticmethod
    def listar_jornadas(
        estado=None,
        cerrada=None,
        fecha=None
    ):

        query = Jornada.query

        if estado is not None:
            query = query.filter(
                Jornada.estado == estado
            )

        if fecha:

            try:
                fecha = JornadaService._convertir_fecha(
                    fecha,
                    "fecha"
                )

            except ValueError as e:
                return {
                    "error": str(e)
                }, 400

            # Jornadas donde la fecha buscada esté
            # dentro del rango inicio-fin
            query = query.filter(
                Jornada.fecha_inicio <= fecha,
                Jornada.fecha_fin >= fecha
            )

        jornadas = query.order_by(
            Jornada.fecha_inicio.desc()
        ).all()

        resultado = [
            JornadaService._jornada_json(jornada)
            for jornada in jornadas
        ]

        return {
            "jornadas": resultado
        }, 200

    # ==========================================
    # OBTENER UNA JORNADA
    # ==========================================

    @staticmethod
    def obtener_jornada(id_jornada):

        jornada = Jornada.query.get(id_jornada)

        if not jornada:
            return {
                "error": "La jornada no existe."
            }, 404

        return {
            "jornada": JornadaService._jornada_json(
                jornada
            )
        }, 200

    # ==========================================
    # EDITAR
    # ==========================================

    @staticmethod
    def editar_jornada(
        id_jornada,
        nombre,
        direccion,
        fecha_inicio,
        fecha_fin
    ):

        jornada = Jornada.query.get(id_jornada)

        if not jornada:
            return {
                "error": "La jornada no existe."
            }, 404

        if not jornada.estado:
            return {
                "error": "No se puede modificar una jornada finalizada."
            }, 400
        
        if not nombre:
            return {
                "error": "El nombre de la jornada es obligatorio."
            }, 400

        if not direccion:
            return {
                "error": "La dirección es obligatoria."
            }, 400

        try:

            fecha_inicio = JornadaService._convertir_fecha(
                fecha_inicio,
                "fecha_inicio"
            )

            fecha_fin = JornadaService._convertir_fecha(
                fecha_fin,
                "fecha_fin"
            )

        except ValueError as e:
            return {
                "error": str(e)
            }, 400

        if fecha_fin < fecha_inicio:
            return {
                "error": "La fecha de fin no puede ser anterior a la fecha de inicio."
            }, 400

        try:

            jornada.nombre = nombre.strip()
            jornada.direccion = direccion.strip()
            jornada.fecha_inicio = fecha_inicio
            jornada.fecha_fin = fecha_fin

            db.session.commit()

            return {
                "mensaje": "Jornada actualizada correctamente.",
                "jornada": JornadaService._jornada_json(
                    jornada
                )
            }, 200

        except Exception as e:

            db.session.rollback()

            return {
                "error": "No se pudo actualizar la jornada.",
                "detalle": str(e)
            }, 500

    # ==========================================
    # CERRAR JORNADA
    # ==========================================

    @staticmethod
    def cerrar_jornada(id_jornada):

        jornada = Jornada.query.get(id_jornada)

        if not jornada:
            return {
                "error": "La jornada no existe."
            }, 404

        if not jornada.estado:
            return {
                "error": "La jornada ya se encuentra cerrada."
            }, 400

        try:

            jornada.estado = False

            db.session.commit()

            return {
                "mensaje": "Jornada cerrada correctamente.",
                "jornada": JornadaService._jornada_json(
                    jornada
                )
            }, 200

        except Exception as e:

            db.session.rollback()

            return {
                "error": "No se pudo cerrar la jornada.",
                "detalle": str(e)
            }, 500

    # ==========================================
    # ELIMINACIÓN LÓGICA
    # ==========================================

    @staticmethod
    def eliminar_jornada(id_jornada):

        jornada = Jornada.query.get(id_jornada)

        if not jornada:
            return {
                "error": "La jornada no existe."
            }, 404

        if not jornada.estado:
            return {
                "error": "La jornada ya se encuentra inactiva."
            }, 400

        try:

            jornada.estado = False

            db.session.commit()

            return {
                "mensaje": "Jornada eliminada correctamente."
            }, 200

        except Exception as e:

            db.session.rollback()

            return {
                "error": "No se pudo eliminar la jornada.",
                "detalle": str(e)
            }, 500

    # ==========================================
    # REACTIVAR
    # ==========================================

    @staticmethod
    def reactivar_jornada(id_jornada):

        jornada = Jornada.query.get(id_jornada)

        if not jornada:
            return {
                "error": "La jornada no existe."
            }, 404

        if jornada.estado:
            return {
                "error": "La jornada ya se encuentra activa."
            }, 400

        try:

            jornada.estado = True

            db.session.commit()

            return {
                "mensaje": "Jornada reactivada correctamente.",
                "jornada": JornadaService._jornada_json(
                    jornada
                )
            }, 200

        except Exception as e:

            db.session.rollback()

            return {
                "error": "No se pudo reactivar la jornada.",
                "detalle": str(e)
            }, 500