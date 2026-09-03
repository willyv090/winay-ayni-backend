from app.extensions import db


class RolPersona(db.Model):
    __tablename__ = "rol_persona"

    id_rol_per = db.Column(db.Integer, primary_key=True)
    estado = db.Column(db.Boolean, nullable=False)

    persona_id_per = db.Column(
        db.Integer,
        db.ForeignKey("persona.id_per"),
        nullable=False
    )

    rol_id_rol = db.Column(
        db.Integer,
        db.ForeignKey("rol.id_rol"),
        nullable=False
    )

    persona = db.relationship("Persona")
    rol = db.relationship("Rol")

    def to_dict(self):
        return {
            "id_rol_per": self.id_rol_per,
            "estado": self.estado,
            "persona_id_per": self.persona_id_per,
            "rol_id_rol": self.rol_id_rol
        }