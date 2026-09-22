from datetime import date
from decimal import Decimal, InvalidOperation

from app.extensions import db
from app.models.producto import Producto
from app.models.empresa import Empresa


class ProductoService:

    # ==========================================
    # MÉTODOS AUXILIARES
    # ==========================================

    @staticmethod
    def _convertir_decimal(valor, nombre_campo):
        try:
            return Decimal(str(valor))
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError(
                f"El campo {nombre_campo} debe ser un número válido."
            )

    @staticmethod
    def _convertir_fecha(valor, nombre_campo, obligatorio=False):

        if not valor:
            if obligatorio:
                raise ValueError(
                    f"El campo {nombre_campo} es obligatorio."
                )

            return None

        if isinstance(valor, date):
            return valor

        try:
            return date.fromisoformat(valor)
        except (TypeError, ValueError):
            raise ValueError(
                f"El campo {nombre_campo} debe tener formato YYYY-MM-DD."
            )

    @staticmethod
    def _producto_json(producto):

        rebaja = (
            Decimal(producto.rebaja)
            if producto.rebaja is not None
            else Decimal("0")
        )

        precio = Decimal(producto.precio_u)

        precio_final = precio - rebaja

        return {
            "id": producto.id_prod,
            "nombre": producto.nombre,
            "cantidad": producto.cantidad,
            "precio_u": float(precio),
            "rebaja": float(rebaja),
            "precio_final": float(precio_final),
            "fecha_ingreso": (
                producto.fecha_ingreso.isoformat()
                if producto.fecha_ingreso
                else None
            ),
            "fecha_salida": (
                producto.fecha_salida.isoformat()
                if producto.fecha_salida
                else None
            ),
            "notas": producto.notas,
            "estado": producto.estado,
            "empresa": {
                "id": producto.empresa.id_empresa,
                "nombre": producto.empresa.nombre
            }
        }

    # ==========================================
    # CREAR PRODUCTO
    # ==========================================

    @staticmethod
    def crear_producto(
        nombre,
        cantidad,
        precio_u,
        rebaja,
        fecha_ingreso,
        fecha_salida,
        notas,
        id_empresa
    ):

        if not nombre:
            return {
                "error": "El nombre del producto es obligatorio."
            }, 400

        if cantidad is None:
            return {
                "error": "La cantidad inicial es obligatoria."
            }, 400

        try:
            cantidad = int(cantidad)
        except (TypeError, ValueError):
            return {
                "error": "La cantidad debe ser un número entero."
            }, 400

        if cantidad < 0:
            return {
                "error": "La cantidad no puede ser negativa."
            }, 400

        if precio_u is None:
            return {
                "error": "El precio unitario es obligatorio."
            }, 400

        try:
            precio_u = ProductoService._convertir_decimal(
                precio_u,
                "precio_u"
            )

            rebaja = ProductoService._convertir_decimal(
                rebaja if rebaja is not None else 0,
                "rebaja"
            )

            fecha_ingreso = ProductoService._convertir_fecha(
                fecha_ingreso,
                "fecha_ingreso",
                obligatorio=True
            )

            fecha_salida = ProductoService._convertir_fecha(
                fecha_salida,
                "fecha_salida"
            )

        except ValueError as e:
            return {
                "error": str(e)
            }, 400

        if precio_u <= 0:
            return {
                "error": "El precio unitario debe ser mayor a cero."
            }, 400

        if rebaja < 0:
            return {
                "error": "La rebaja no puede ser negativa."
            }, 400

        if rebaja > precio_u:
            return {
                "error": "La rebaja no puede ser mayor al precio unitario."
            }, 400

        empresa = Empresa.query.filter_by(
            id_empresa=id_empresa,
            estado=True
        ).first()

        if not empresa:
            return {
                "error": "La empresa no existe o se encuentra inactiva."
            }, 404

        nombre = nombre.strip()

        if notas:
            notas = notas.strip()

        try:

            nuevo_producto = Producto(
                nombre=nombre,
                cantidad=cantidad,
                precio_u=precio_u,
                rebaja=rebaja,
                fecha_ingreso=fecha_ingreso,
                fecha_salida=fecha_salida,
                notas=notas,
                empresa_id_empresa=id_empresa,
                estado=True
            )

            db.session.add(nuevo_producto)
            db.session.commit()

            return {
                "mensaje": "Producto creado correctamente.",
                "producto": ProductoService._producto_json(
                    nuevo_producto
                )
            }, 201

        except Exception as e:

            db.session.rollback()

            return {
                "error": "No se pudo registrar el producto.",
                "detalle": str(e)
            }, 500

    # ==========================================
    # LISTAR PRODUCTOS
    # ==========================================

    @staticmethod
    def listar_productos():

        productos = Producto.query.order_by(
            Producto.id_prod
        ).all()

        resultado = [
            ProductoService._producto_json(producto)
            for producto in productos
        ]

        return {
            "productos": resultado
        }, 200

    #==========================================
    # OBTENER PRODUCTOS POR EMPRESA Y FILTRAR POR NOMBRE
    #==========================================

    @staticmethod
    def listar_productos_empresa(id_empresa, buscar=None):

        empresa = Empresa.query.filter_by(
            id_empresa=id_empresa,
            estado=True
        ).first()

        if not empresa:
            return {
                "error": "La empresa no existe o se encuentra inactiva."
            }, 404

        query = Producto.query.filter_by(
            empresa_id_empresa=id_empresa,
            estado=True
        )

        if buscar:
            buscar = buscar.strip()

            query = query.filter(
                Producto.nombre.ilike(f"%{buscar}%")
            )

        productos = query.order_by(
            Producto.nombre
        ).all()

        resultado = [
            ProductoService._producto_json(producto)
            for producto in productos
        ]

        return {
            "empresa": {
                "id": empresa.id_empresa,
                "nombre": empresa.nombre
            },
            "productos": resultado
        }, 200

    # ==========================================
    # OBTENER PRODUCTO
    # ==========================================

    @staticmethod
    def obtener_producto(id_producto):

        producto = Producto.query.get(id_producto)

        if not producto:
            return {
                "error": "El producto no existe."
            }, 404

        return {
            "producto": ProductoService._producto_json(producto)
        }, 200

    # ==========================================
    # EDITAR PRODUCTO
    # ==========================================

    @staticmethod
    def editar_producto(
        id_producto,
        nombre,
        precio_u,
        rebaja,
        fecha_ingreso,
        fecha_salida,
        notas,
        id_empresa
    ):

        producto = Producto.query.get(id_producto)

        if not producto:
            return {
                "error": "El producto no existe."
            }, 404

        if not producto.estado:
            return {
                "error": "No se puede modificar un producto inactivo."
            }, 400

        if not nombre:
            return {
                "error": "El nombre del producto es obligatorio."
            }, 400

        if precio_u is None:
            return {
                "error": "El precio unitario es obligatorio."
            }, 400

        try:

            precio_u = ProductoService._convertir_decimal(
                precio_u,
                "precio_u"
            )

            rebaja = ProductoService._convertir_decimal(
                rebaja if rebaja is not None else 0,
                "rebaja"
            )

            fecha_ingreso = ProductoService._convertir_fecha(
                fecha_ingreso,
                "fecha_ingreso",
                obligatorio=True
            )

            fecha_salida = ProductoService._convertir_fecha(
                fecha_salida,
                "fecha_salida"
            )

        except ValueError as e:
            return {
                "error": str(e)
            }, 400

        if precio_u <= 0:
            return {
                "error": "El precio unitario debe ser mayor a cero."
            }, 400

        if rebaja < 0:
            return {
                "error": "La rebaja no puede ser negativa."
            }, 400

        if rebaja > precio_u:
            return {
                "error": "La rebaja no puede ser mayor al precio unitario."
            }, 400

        empresa = Empresa.query.filter_by(
            id_empresa=id_empresa,
            estado=True
        ).first()

        if not empresa:
            return {
                "error": "La empresa no existe o se encuentra inactiva."
            }, 404

        try:

            producto.nombre = nombre.strip()
            producto.precio_u = precio_u
            producto.rebaja = rebaja
            producto.fecha_ingreso = fecha_ingreso
            producto.fecha_salida = fecha_salida
            producto.notas = notas.strip() if notas else None
            producto.empresa_id_empresa = id_empresa

            db.session.commit()

            return {
                "mensaje": "Producto actualizado correctamente.",
                "producto": ProductoService._producto_json(
                    producto
                )
            }, 200

        except Exception as e:

            db.session.rollback()

            return {
                "error": "No se pudo actualizar el producto.",
                "detalle": str(e)
            }, 500

    # ==========================================
    # ELIMINAR PRODUCTO
    # ==========================================

    @staticmethod
    def eliminar_producto(id_producto):

        producto = Producto.query.get(id_producto)

        if not producto:
            return {
                "error": "El producto no existe."
            }, 404

        if not producto.estado:
            return {
                "error": "El producto ya se encuentra inactivo."
            }, 400

        try:

            producto.estado = False

            db.session.commit()

            return {
                "mensaje": "Producto eliminado correctamente."
            }, 200

        except Exception as e:

            db.session.rollback()

            return {
                "error": "No se pudo eliminar el producto.",
                "detalle": str(e)
            }, 500

    # ==========================================
    # REACTIVAR PRODUCTO
    # ==========================================

    @staticmethod
    def reactivar_producto(id_producto):

        producto = Producto.query.get(id_producto)

        if not producto:
            return {
                "error": "El producto no existe."
            }, 404

        if producto.estado:
            return {
                "error": "El producto ya se encuentra activo."
            }, 400

        empresa = Empresa.query.filter_by(
            id_empresa=producto.empresa_id_empresa,
            estado=True
        ).first()

        if not empresa:
            return {
                "error": "No se puede reactivar el producto porque su empresa se encuentra inactiva."
            }, 400

        try:

            producto.estado = True

            db.session.commit()

            return {
                "mensaje": "Producto reactivado correctamente.",
                "producto": ProductoService._producto_json(
                    producto
                )
            }, 200

        except Exception as e:

            db.session.rollback()

            return {
                "error": "No se pudo reactivar el producto.",
                "detalle": str(e)
            }, 500

    # ==========================================
    # AJUSTAR INVENTARIO
    # ==========================================

    @staticmethod
    def ajustar_stock(id_producto, ajuste, notas=None):

        producto = Producto.query.get(id_producto)

        if not producto:
            return {
                "error": "El producto no existe."
            }, 404

        if not producto.estado:
            return {
                "error": "El producto se encuentra inactivo."
            }, 400

        if ajuste is None:
            return {
                "error": "El ajuste de inventario es obligatorio."
            }, 400

        try:
            ajuste = int(ajuste)
        except (TypeError, ValueError):
            return {
                "error": "El ajuste debe ser un número entero."
            }, 400

        if ajuste == 0:
            return {
                "error": "El ajuste debe ser diferente de cero."
            }, 400

        nueva_cantidad = producto.cantidad + ajuste

        if nueva_cantidad < 0:
            return {
                "error": "No existe stock suficiente para realizar el retiro."
            }, 400

        try:

            stock_anterior = producto.cantidad

            producto.cantidad = nueva_cantidad

            if notas:
                producto.notas = notas.strip()

            db.session.commit()

            return {
                "mensaje": "Inventario actualizado correctamente.",
                "inventario": {
                    "producto_id": producto.id_prod,
                    "producto": producto.nombre,
                    "stock_anterior": stock_anterior,
                    "ajuste": ajuste,
                    "stock_actual": producto.cantidad
                }
            }, 200

        except Exception as e:

            db.session.rollback()

            return {
                "error": "No se pudo actualizar el inventario.",
                "detalle": str(e)
            }, 500