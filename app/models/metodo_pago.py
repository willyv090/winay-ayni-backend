from app.extensions import db


class MetodoPago(db.Model):
    __tablename__ = "metodospago"

    id_metodos = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.Text, nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    estado = db.Column(db.Boolean, nullable=False)

    def to_dict(self):
        return {
            "id_metodos": self.id_metodos,
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "estado": self.estado
        }