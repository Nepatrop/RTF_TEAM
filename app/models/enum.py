import enum


class InterviewTypeEnum(enum.Enum):
    TEXT = "text"
    AUDIO = "audio"


class InterviewStatusEnum(enum.Enum):
    CREATED = "created"
    ACTIVE = "active"
    QUESTION = "question"
    DONE = "done"
    ERROR = "error"


class SessionStatusEnum(enum.Enum):
    PROCESSING = "processing"
    GENERATING_QUESTIONS = "generating_questions"
    WAITING_FOR_ANSWERS = "waiting_for_answers"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"


class SessionMessageTypeEnum(enum.Enum):
    QUESTION = "question"
    ANSWER = "answer"
    RESULT = "result"


class SessionMessageRoleEnum(enum.Enum):
    AGENT = "agent"
    USER = "user"


class SessionCallbackEnum(enum.Enum):
    QUESTIONS = "questions"
    FINAL_RESULT = "finalResult"
    PROJECT_UPDATED = "projectUpdated"
