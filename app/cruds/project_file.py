from app.cruds import BaseCRUD
from app.models import ProjectFile as ProjectFileORM


class ProjectFileCRUD(BaseCRUD):
    model = ProjectFileORM
