from models import db

class Template(db.Model):
    __tablename__ = 'templates'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    description = db.Column(db.Text)
    name = db.Column(db.String(255))
    image = db.Column(db.String(255))
    cpu_limit = db.Column(db.String(50))
    mem_limit = db.Column(db.String(50))
    disk_limit = db.Column(db.String(50))
    command = db.Column(db.Text)
    available_command = db.Column(db.Text)
    tags = db.Column(db.Text)
    container_port = db.Column(db.Integer)

    containers = db.relationship('Container', backref='template', lazy=True)

    @classmethod
    def get_by_id(cls, template_id):
        return cls.query.get(template_id)

    @classmethod
    def create_template(cls, description, name, image, cpu_limit, mem_limit,
                        disk_limit, command, available_command, tags, container_port):
        template = cls(
            description=description,
            name=name,
            image=image,
            cpu_limit=cpu_limit,
            mem_limit=mem_limit,
            disk_limit=disk_limit,
            command=command,
            available_command=available_command,
            tags=tags,
            container_port=container_port
        )
        db.session.add(template)
        db.session.commit()
        return template

    def to_dict(self):
        return {
            'id': self.id,
            'description': self.description,
            'name': self.name,
            'image': self.image,
            'cpu_limit': self.cpu_limit,
            'mem_limit': self.mem_limit,
            'disk_limit': self.disk_limit,
            'command': self.command,
            'available_command': self.available_command,
            'tags': self.tags,
            'container_port': self.container_port
        }