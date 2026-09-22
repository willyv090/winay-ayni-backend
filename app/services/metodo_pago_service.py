from app.extensions import db
from app.models.metodo_pago import MetodoPago


class MetodoPagoService:

    # ==========================================
    # CREAR
    # ==========================================

    @staticmethod
    def crear_metodo_pago(nombre, descripcion):

        if not nombre:
            return {
                "error": "El nombre del método de pago es obligatorio."
            }, 400

        if not descripcion:
            return {
                "error": "La descripción es obligatoria."
            }, 400

        nombre = nombre.strip().upper()
        descripcion = descripcion.strip()

        metodo_existente = MetodoPago.query.filter(
            db.func.lower(MetodoPago.nombre) == nombre.lower()
        ).first()

        if metodo_existente:
            return {
                "error": "El método de pago ya se encuentra registrado."
            }, 409

        try:

            nuevo_metodo = MetodoPago(
                nombre=nombre,
                descripcion=descripcion,
                estado=True
            )

            db.session.add(nuevo_metodo)
            db.session.commit()

            return {
                "mensaje": "Metodo de pago creado correctamente.",
                "metodo_pago": {
                    "id": nuevo_metodo.id_metodos,
                    "nombre": nuevo_metodo.nombre,
                    "descripcion": nuevo_metodo.descripcion,
                    "estado": nuevo_metodo.estado
                }
            }, 201

        except Exception as e:

            db.session.rollback()

            return {
                "error": "No se pudo registrar el método de pago.",
                "detalle": str(e)
            }, 500

    # ==========================================
    # LISTAR
    # ==========================================

    @staticmethod
    def listar_metodos_pago(estado=None):

        query = MetodoPago.query

        if estado is not None:
            query = query.filter(
                MetodoPago.estado == estado
            )

        metodos = query.order_by(
            MetodoPago.nombre
        ).all()

        resultado = []

        for metodo in metodos:

            resultado.append({
                "id": metodo.id_metodos,
                "nombre": metodo.nombre,
                "descripcion": metodo.descripcion,
                "estado": metodo.estado
            })

        return {
            "metodos_pago": resultado
        }, 200

    # ==========================================
    # OBTENER UNO
    # ==========================================

    @staticmethod
    def obtener_metodo_pago(id_metodo):

        metodo = MetodoPago.query.get(id_metodo)

        if not metodo:
            return {
                "error": "El método de pago no existe."
            }, 404

        return {
            "metodo_pago": {
                "id": metodo.id_metodos,
                "nombre": metodo.nombre,
                "descripcion": metodo.descripcion,
                "estado": metodo.estado
            }
        }, 200

    # ==========================================
    # EDITAR
    # ==========================================

    @staticmethod
    def editar_metodo_pago(
        id_metodo,
        nombre,
        descripcion
    ):

        metodo = MetodoPago.query.get(id_metodo)

        if not metodo:
            return {
                "error": "El método de pago no existe."
            }, 404

        if not metodo.estado:
            return {
                "error": "No se puede modificar un método de pago inactivo."
            }, 400

        if not nombre:
            return {
                "error": "El nombre del método de pago es obligatorio."
            }, 400

        if not descripcion:
            return {
                "error": "La descripción es obligatoria."
            }, 400

        nombre = nombre.strip().upper()
        descripcion = descripcion.strip()

        metodo_existente = MetodoPago.query.filter(
            db.func.lower(MetodoPago.nombre) == nombre.lower(),
            MetodoPago.id_metodos != id_metodo
        ).first()

        if metodo_existente:
            return {
                "error": "Ya existe otro método de pago con ese nombre."
            }, 409

        try:

            metodo.nombre = nombre
            metodo.descripcion = descripcion

            db.session.commit()

            return {
                "mensaje": "Método de pago actualizado correctamente.",
                "metodo_pago": {
                    "id": metodo.id_metodos,
                    "nombre": metodo.nombre,
                    "descripcion": metodo.descripcion,
                    "estado": metodo.estado
                }
            }, 200

        except Exception as e:

            db.session.rollback()

            return {
                "error": "No se pudo actualizar el método de pago.",
                "detalle": str(e)
            }, 500

    # ==========================================
    # DESACTIVAR
    # ==========================================

    @staticmethod
    def eliminar_metodo_pago(id_metodo):

        metodo = MetodoPago.query.get(id_metodo)

        if not metodo:
            return {
                "error": "El método de pago no existe."
            }, 404

        if not metodo.estado:
            return {
                "error": "El método de pago ya se encuentra inactivo."
            }, 400

        try:

            metodo.estado = False

            db.session.commit()

            return {
                "mensaje": "Método de pago desactivado correctamente."
            }, 200

        except Exception as e:

            db.session.rollback()

            return {
                "error": "No se pudo desactivar el método de pago.",
                "detalle": str(e)
            }, 500

    # ==========================================
    # REACTIVAR
    # ==========================================

    @staticmethod
    def reactivar_metodo_pago(id_metodo):

        metodo = MetodoPago.query.get(id_metodo)

        if not metodo:
            return {
                "error": "El método de pago no existe."
            }, 404

        if metodo.estado:
            return {
                "error": "El método de pago ya se encuentra activo."
            }, 400

        try:

            metodo.estado = True

            db.session.commit()

            return {
                "mensaje": "Método de pago reactivado correctamente.",
                "metodo_pago": {
                    "id": metodo.id_metodos,
                    "nombre": metodo.nombre,
                    "descripcion": metodo.descripcion,
                    "estado": metodo.estado
                }
            }, 200

        except Exception as e:

            db.session.rollback()

            return {
                "error": "No se pudo reactivar el método de pago.",
                "detalle": str(e)
            }, 500