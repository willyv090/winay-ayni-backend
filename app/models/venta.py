from app.extensions import db


class Venta(db.Model):
    __tablename__ = "venta"

    __table_args__ = (
        db.CheckConstraint(
            "tipo IN ('JORNADA', 'INDEPENDIENTE')",
            name="ck_venta_tipo"
        ),
        db.CheckConstraint(
            "(tipo = 'JORNADA' AND jornadacajero_id_jor_caj IS NOT NULL) OR "
            "(tipo = 'INDEPENDIENTE' AND jornadacajero_id_jor_caj IS NULL)",
            name="ck_venta_tipo_asignacion"
        ),
        db.Index("ix_venta_persona_fecha", "persona_id_per", "fecha"),
    )

    tipo = db.Column(db.String(15), nullable=False)
    persona_id_per = db.Column(
        db.Integer,
        db.ForeignKey("persona.id_per", name="fk_venta_persona_responsable"),
        nullable=False
    )
    # Los registros históricos pueden no tener fecha de registro conocida.
    fecha_registro = db.Column(
        db.DateTime(timezone=False),
        nullable=True,
        server_default=db.text("CURRENT_TIMESTAMP")
    )

    id_venta = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)

    jornada_cajero_id_jor_caj = db.Column(
        "jornadacajero_id_jor_caj",
        db.Integer,
        db.ForeignKey("jornadacajero.id_jor_caj"),
        nullable=True
    )

    metodos_pago_id_metodos = db.Column(
        "metodospago_id_metodos",
        db.Integer,
        db.ForeignKey("metodospago.id_metodos"),
        nullable=False
    )

    persona = db.relationship("Persona")
    jornada_cajero = db.relationship("JornadaCajero")
    metodo_pago = db.relationship("MetodoPago")

    def to_dict(self):
        return {
            "id_venta": self.id_venta,
            "tipo": self.tipo,
            "persona_id_per": self.persona_id_per,
            "fecha_registro": (
                self.fecha_registro.isoformat() if self.fecha_registro else None
            ),
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "total": float(self.total),
            "jornada_cajero_id_jor_caj": self.jornada_cajero_id_jor_caj,
            "metodos_pago_id_metodos": self.metodos_pago_id_metodos
        }