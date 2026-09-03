from app.extensions import db


class JornadaCajero(db.Model):
    __tablename__ = "jornadacajero"

    id_jor_caj = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False)
    estado = db.Column(db.Boolean, nullable=False)

    jornada_id_jornada = db.Column(
        db.Integer,
        db.ForeignKey("jornada.id_jornada"),
        nullable=False
    )

    persona_id_per = db.Column(
        db.Integer,
        db.ForeignKey("persona.id_per"),
        nullable=False
    )

    jornada = db.relationship("Jornada")
    persona = db.relationship("Persona")

    def to_dict(self):
        return {
            "id_jor_caj": self.id_jor_caj,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "estado": self.estado,
            "jornada_id_jornada": self.jornada_id_jornada,
            "persona_id_per": self.persona_id_per
        }