import enum


class InterviewTypeEnum(enum.Enum):
    TEXT = "text"
    TEXT_FILE = "text_file"
    AUDIO = "audio"

class InterviewStatusEnum(enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    QUESTION = "question"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"