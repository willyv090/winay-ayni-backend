from datetime import date

from app.extensions import db
from app.models.jornada import Jornada
from app.models.producto import Producto
from app.models.empresa import Empresa
from app.models.jornada_producto import JornadaProducto


class JornadaProductoService:

    @staticmethod
    def asignar_productos(
        id_jornada,
        id_empresa,
        productos
    ):

        jornada = Jornada.query.get(id_jornada)

        if not jornada:
            return {
                "error": "La jornada no existe."
            }, 404

        if not jornada.estado:
            return {
                "error": "No se pueden asignar productos a una jornada finalizada."
            }, 400

        empresa = Empresa.query.filter_by(
            id_empresa=id_empresa,
            estado=True
        ).first()

        if not empresa:
            return {
                "error": "La empresa no existe o se encuentra inactiva."
            }, 404

        if not isinstance(productos, list):
            return {
                "error": "El campo productos debe ser una lista."
            }, 400

        if len(productos) == 0:
            return {
                "error": "Debe seleccionar al menos un producto."
            }, 400

        # Quitar IDs repetidos
        productos = list(set(productos))

        # Buscar únicamente productos:
        # - seleccionados
        # - activos
        # - pertenecientes a la empresa seleccionada
        productos_validos = Producto.query.filter(
            Producto.id_prod.in_(productos),
            Producto.empresa_id_empresa == id_empresa,
            Producto.estado == True
        ).all()

        ids_validos = {
            producto.id_prod
            for producto in productos_validos
        }

        if ids_validos != set(productos):
            return {
                "error": "Uno o más productos no existen, están inactivos o no pertenecen a la empresa seleccionada."
            }, 400

        try:

            relaciones = JornadaProducto.query.filter_by(
                jornada_id_jornada=id_jornada
            ).all()

            relaciones_por_producto = {
                relacion.producto_id_prod: relacion
                for relacion in relaciones
            }

            for id_producto in productos:

                # Ya estuvo anteriormente en la jornada
                if id_producto in relaciones_por_producto:

                    relacion = relaciones_por_producto[id_producto]

                    relacion.estado = True
                    relacion.fecha = date.today()

                else:

                    nueva_relacion = JornadaProducto(
                        fecha=date.today(),
                        estado=True,
                        producto_id_prod=id_producto,
                        jornada_id_jornada=id_jornada
                    )

                    db.session.add(nueva_relacion)

            db.session.commit()

            return {
                "mensaje": "Productos asignados correctamente.",
                "empresa": {
                    "id": empresa.id_empresa,
                    "nombre": empresa.nombre
                },
                "productos_asignados": productos
            }, 200

        except Exception as e:

            db.session.rollback()

            return {
                "error": "No se pudieron asignar los productos.",
                "detalle": str(e)
            }, 500
    # ======================================
    # LISTAR PRODUCTOS DE LA JORNADA
    # ======================================

    @staticmethod
    def listar_productos(id_jornada):

        jornada = Jornada.query.get(id_jornada)

        if not jornada:
            return {
                "error": "La jornada no existe."
            }, 404

        relaciones = JornadaProducto.query.filter_by(
            jornada_id_jornada=id_jornada
        ).order_by(
            JornadaProducto.id_jor_prod
        ).all()

        resultado = []

        for relacion in relaciones:

            producto = relacion.producto

            rebaja = float(producto.rebaja or 0)
            precio = float(producto.precio_u)

            resultado.append({
                "id_jornada_producto": relacion.id_jor_prod,
                "fecha": relacion.fecha.isoformat(),
                "estado": relacion.estado,
                "producto": {
                    "id": producto.id_prod,
                    "nombre": producto.nombre,
                    "cantidad": producto.cantidad,
                    "precio_u": precio,
                    "rebaja": rebaja,
                    "precio_final": precio - rebaja,
                    "empresa_id": producto.empresa_id_empresa
                }
            })

        return {
            "jornada": {
                "id": jornada.id_jornada,
                "nombre": jornada.nombre,
                "estado": jornada.estado
            },
            "productos": resultado
        }, 200

    # ======================================
    # QUITAR PRODUCTO
    # ======================================

    @staticmethod
    def quitar_producto(id_jornada, id_producto):

        jornada = Jornada.query.get(id_jornada)

        if not jornada:
            return {
                "error": "La jornada no existe."
            }, 404

        if not jornada.estado:
            return {
                "error": "No se puede modificar una jornada finalizada."
            }, 400

        relacion = JornadaProducto.query.filter_by(
            jornada_id_jornada=id_jornada,
            producto_id_prod=id_producto
        ).first()

        if not relacion:
            return {
                "error": "El producto no está asignado a esta jornada."
            }, 404

        if not relacion.estado:
            return {
                "error": "El producto ya se encuentra desvinculado."
            }, 400

        try:

            relacion.estado = False

            db.session.commit()

            return {
                "mensaje": "Producto retirado de la jornada correctamente."
            }, 200

        except Exception as e:

            db.session.rollback()

            return {
                "error": "No se pudo retirar el producto.",
                "detalle": str(e)
            }, 500