from app.extensions import db


class Venta(db.Model):
    __tablename__ = "venta"

    id_venta = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)

    jornada_cajero_id_jor_caj = db.Column(
        db.Integer,
        db.ForeignKey("jornadacajero.id_jor_caj"),
        nullable=False
    )

    metodos_pago_id_metodos = db.Column(
        db.Integer,
        db.ForeignKey("metodospago.id_metodos"),
        nullable=False
    )

    jornada_cajero = db.relationship("JornadaCajero")
    metodo_pago = db.relationship("MetodoPago")

    def to_dict(self):
        return {
            "id_venta": self.id_venta,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "total": float(self.total),
            "jornada_cajero_id_jor_caj": self.jornada_cajero_id_jor_caj,
            "metodos_pago_id_metodos": self.metodos_pago_id_metodos
        }