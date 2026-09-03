from app.extensions import db


class Producto(db.Model):
    __tablename__ = "producto"

    id_prod = db.Column(db.Integer, primary_key=True)

    nombre = db.Column(db.Text, nullable=False)
    cantidad = db.Column(db.BigInteger, nullable=False)
    precio_u = db.Column(db.Numeric(10, 2), nullable=False)
    rebaja = db.Column(db.Numeric(10, 2), nullable=True)

    fecha_ingreso = db.Column(db.Date, nullable=False)
    fecha_salida = db.Column(db.Date, nullable=True)

    estado = db.Column(db.Boolean, nullable=False)
    notas = db.Column(db.Text, nullable=True)

    empresa_id_empresa = db.Column(
        db.Integer,
        db.ForeignKey("empresa.id_empresa"),
        nullable=False
    )

    empresa = db.relationship("Empresa")

    def to_dict(self):
        return {
            "id_prod": self.id_prod,
            "nombre": self.nombre,
            "cantidad": self.cantidad,
            "precio_u": float(self.precio_u),
            "rebaja": float(self.rebaja) if self.rebaja is not None else None,
            "fecha_ingreso": (
                self.fecha_ingreso.isoformat()
                if self.fecha_ingreso else None
            ),
            "fecha_salida": (
                self.fecha_salida.isoformat()
                if self.fecha_salida else None
            ),
            "estado": self.estado,
            "empresa_id_empresa": self.empresa_id_empresa,
            "notas": self.notas
        }