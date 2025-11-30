from app.cruds import BaseCRUD
from app.models import InterviewFile as InterviewFileORM


class InterviewFileCRUD(BaseCRUD):
    model = InterviewFileORM
