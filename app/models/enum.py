import enum


class InterviewTypeEnum(enum.Enum):
    TEXT = "text"
    AUDIO = "audio"


class InterviewStatusEnum(enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    QUESTION = "question"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"
