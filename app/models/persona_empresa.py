from app.extensions import db


class PersonaEmpresa(db.Model):
    __tablename__ = "pers_emp"

    id_per_emo = db.Column(db.Integer, primary_key=True)
    estado = db.Column(db.Boolean, nullable=False)

    empresa_id_empresa = db.Column(
        db.Integer,
        db.ForeignKey("empresa.id_empresa"),
        nullable=False
    )

    persona_id_per = db.Column(
        db.Integer,
        db.ForeignKey("persona.id_per"),
        nullable=False
    )

    empresa = db.relationship("Empresa")
    persona = db.relationship("Persona")

    def to_dict(self):
        return {
            "id_per_emo": self.id_per_emo,
            "estado": self.estado,
            "empresa_id_empresa": self.empresa_id_empresa,
            "persona_id_per": self.persona_id_per
        }