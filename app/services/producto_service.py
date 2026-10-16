from datetime import date
from decimal import Decimal, InvalidOperation

from app.extensions import db
from app.models.producto import Producto
from app.models.empresa import Empresa
from app.models.persona import Persona
from app.models.rol import Rol
from app.models.rol_persona import RolPersona
from app.services.empresa_service import EmpresaService


class ProductoService:
    @staticmethod
    def autorizar(id_persona, escritura=False, propio=False, id_empresa=None, id_producto=None):
        try:
            id_persona = int(id_persona)
        except (ValueError, TypeError):
            return {"error": "Usuario inválido."}, 403, True
        persona = db.session.get(Persona, id_persona)
        if not persona or not persona.estado:
            return {"error": "El usuario no está activo."}, 403, True
        roles = {r.nombre for r in Rol.query.join(
            RolPersona, RolPersona.rol_id_rol == Rol.id_rol
        ).filter(RolPersona.persona_id_per == id_persona,
                 RolPersona.estado.is_(True), Rol.estado.is_(True)).all()}
        restringido = escritura or propio or "ADMINISTRADOR" not in roles
        if restringido and "EMPRENDEDOR" not in roles:
            return {"error": "Se requiere el rol emprendedor."}, 403, True
        if id_producto is not None:
            producto = db.session.get(Producto, id_producto)
            if not producto:
                return {"error": "Producto no disponible."}, 404, restringido
            # Validar también la empresa destino en edición.
            origen = producto.empresa_id_empresa
            if restringido and EmpresaService.consulta_propias(id_persona).filter(
                Empresa.id_empresa == origen
            ).first() is None:
                return {"error": "Producto no disponible."}, 404, True
            if escritura and not producto.empresa.estado:
                return {"error": "La empresa se encuentra inactiva."}, 400, restringido
            if id_empresa is None:
                id_empresa = origen
        if id_empresa is not None:
            try:
                if isinstance(id_empresa, bool) or str(int(id_empresa)) != str(id_empresa):
                    raise ValueError()
                id_empresa = int(id_empresa)
            except (TypeError, ValueError):
                return {"error": "Seleccione una empresa válida."}, 400, restringido
            query = EmpresaService.consulta_propias(id_persona) if restringido else Empresa.query
            empresa = query.filter(Empresa.id_empresa == id_empresa).first()
            if empresa is None:
                return {"error": "Empresa no disponible."}, 404, restringido
            if escritura and not empresa.estado:
                return {"error": "La empresa se encuentra inactiva."}, 400, restringido
        elif escritura and id_producto is None:
            return {"error": "Seleccione una empresa."}, 400, restringido
        return None, 200, restringido


    # ==========================================
    # MÉTODOS AUXILIARES
    # ==========================================

    @staticmethod
    def _convertir_decimal(valor, nombre_campo):
        try:
            numero = Decimal(str(valor))
            if not numero.is_finite():
                raise InvalidOperation()
            return numero
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

        if not isinstance(nombre, str) or not nombre.strip():
            return {
                "error": "El nombre del producto es obligatorio."
            }, 400

        if cantidad is None:
            return {
                "error": "La cantidad inicial es obligatoria."
            }, 400

        try:
            if isinstance(cantidad, bool) or Decimal(str(cantidad)) != int(cantidad):
                raise ValueError()
            cantidad = int(cantidad)
        except (TypeError, ValueError, InvalidOperation, OverflowError):
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

        if fecha_salida and fecha_salida < fecha_ingreso:
            return {"error": "La fecha de salida no puede ser anterior al ingreso."}, 400
        if notas is not None and not isinstance(notas, str):
            return {"error": "Las notas deben ser texto."}, 400

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
    def listar_productos(id_persona=None):

        query = Producto.query
        if id_persona is not None:
            query = query.filter(Producto.empresa_id_empresa.in_(
                EmpresaService.consulta_propias(id_persona).with_entities(Empresa.id_empresa)
            ))
        productos = query.order_by(Producto.id_prod).all()

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
    def listar_productos_empresa(id_empresa, buscar=None, estado='activos'):
        empresa = db.session.get(Empresa, id_empresa)
        if not empresa:
            return {"error": "La empresa no existe."}, 404
        if estado not in ("activos", "archivados", "todos"):
            return {"error": "Estado de productos inválido."}, 400
        query = Producto.query.filter_by(empresa_id_empresa=id_empresa)
        if estado != "todos":
            query = query.filter(Producto.estado == (estado == "activos"))

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

        if not isinstance(nombre, str) or not nombre.strip():
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

        if fecha_salida and fecha_salida < fecha_ingreso:
            return {"error": "La fecha de salida no puede ser anterior al ingreso."}, 400
        if notas is not None and not isinstance(notas, str):
            return {"error": "Las notas deben ser texto."}, 400

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