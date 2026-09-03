from app.extensions import db


class Persona(db.Model):
    __tablename__ = "persona"

    id_per = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.Text, nullable=False)
    usuario = db.Column(db.Text, nullable=False)
    contrasenia = db.Column(db.String(15), nullable=False)
    estado = db.Column(db.Boolean, nullable=False)

    def to_dict(self):
        return {
            "id_per": self.id_per,
            "nombre": self.nombre,
            "usuario": self.usuario,
            "estado": self.estado
        }