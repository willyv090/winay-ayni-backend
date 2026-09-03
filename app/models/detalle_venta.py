from app.extensions import db


class DetalleVenta(db.Model):
    __tablename__ = "detalleventa"

    id_detalle = db.Column(db.Integer, primary_key=True)

    cantidad = db.Column(db.BigInteger, nullable=False)
    precio_u = db.Column(db.Numeric(10, 2), nullable=False)
    rebaja_aplicada = db.Column(db.Numeric(10, 2), nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)

    venta_id_venta = db.Column(
        db.Integer,
        db.ForeignKey("venta.id_venta"),
        nullable=False
    )

    jornada_producto_id_jor_prod = db.Column(
        db.Integer,
        db.ForeignKey("jornada_producto.id_jor_prod"),
        nullable=False
    )

    venta = db.relationship("Venta")
    jornada_producto = db.relationship("JornadaProducto")

    def to_dict(self):
        return {
            "id_detalle": self.id_detalle,
            "cantidad": self.cantidad,
            "precio_u": float(self.precio_u),
            "rebaja_aplicada": float(self.rebaja_aplicada),
            "subtotal": float(self.subtotal),
            "venta_id_venta": self.venta_id_venta,
            "jornada_producto_id_jor_prod": self.jornada_producto_id_jor_prod
        }