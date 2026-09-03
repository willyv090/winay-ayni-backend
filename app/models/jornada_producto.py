from app.extensions import db


class JornadaProducto(db.Model):
    __tablename__ = "jornada_producto"

    id_jor_prod = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False)
    estado = db.Column(db.Boolean, nullable=False)

    producto_id_prod = db.Column(
        db.Integer,
        db.ForeignKey("producto.id_prod"),
        nullable=False
    )

    jornada_id_jornada = db.Column(
        db.Integer,
        db.ForeignKey("jornada.id_jornada"),
        nullable=False
    )

    producto = db.relationship("Producto")
    jornada = db.relationship("Jornada")

    def to_dict(self):
        return {
            "id_jor_prod": self.id_jor_prod,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "estado": self.estado,
            "producto_id_prod": self.producto_id_prod,
            "jornada_id_jornada": self.jornada_id_jornada
        }