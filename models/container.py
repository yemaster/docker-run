from models import db

class Container(db.Model):
    __tablename__ = 'containers'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255))
    user_id = db.Column(db.String(255))
    template_id = db.Column(db.Integer, db.ForeignKey('templates.id'))
    docker_id = db.Column(db.String(255))
    host_port = db.Column(db.Integer)
    status = db.Column(db.String(50))
    extended_times = db.Column(db.Integer, default=0)
    destroy_time = db.Column(db.DateTime)

    @classmethod
    def get_with_template_info(cls, cont_id):
        from models.template import Template
        cont_with_template = db.session.query(
            cls,
            Template.name.label('template_name'),
            Template.image,
            Template.cpu_limit,
            Template.mem_limit,
            Template.disk_limit,
            Template.command,
            Template.available_command,
            Template.tags,
            Template.container_port,
            Template.description
        ).join(Template, cls.template_id == Template.id)\
         .filter(cls.id == cont_id, cls.status != 'removed')\
         .first()

        if not cont_with_template:
            return None

        container, template_name, image, cpu_limit, mem_limit, disk_limit, command, available_command, tags, container_port, description = cont_with_template

        result = container.to_dict()
        result.update({
            'template_name': template_name,
            'image': image,
            'cpu_limit': cpu_limit,
            'mem_limit': mem_limit,
            'disk_limit': disk_limit,
            'command': command,
            'available_command': available_command,
            'tags': tags,
            'container_port': container_port,
            'description': description
        })
        return result
    

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'user_id': self.user_id,
            'template_id': self.template_id,
            'docker_id': self.docker_id,
            'host_port': self.host_port,
            'status': self.status,
            'extended_times': self.extended_times,
            'destroy_time': self.destroy_time,
        }