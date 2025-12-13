import enum


class InterviewTypeEnum(enum.Enum):
    TEXT = "text"
    AUDIO = "audio"


class InterviewStatusEnum(enum.Enum):
    CREATED = "created" #TO DO убрать
    ACTIVE = "active"
    FINISHED = "finished"


class SessionStatusEnum(enum.Enum):
    PROCESSING = "processing"
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
    ERROR = "error"

class QuestionStatusEnum(enum.Enum):
    UNANSWERED = "unanswered"
    ANSWERED = "answered"
    SKIPPED = "skipped"

class AgentSessionStatusEnum(enum.Enum):
    ASK_USER_GOAL = "ASK_USER_GOAL"
    SELECT_OR_CREATE_PROJECT = "SELECT_OR_CREATE_PROJECT"
    ASK_USER_CONTEXT = "ASK_USER_CONTEXT"
    CHOOSE_MODE = "CHOOSE_MODE"
    WAITING_FOR_ANSWERS = "WAITING_FOR_ANSWERS"
    DRAFT_COLLECTING = "DRAFT_COLLECTING"
    VALIDATING = "VALIDATING"
    GENERATING_REQUIREMENTS = "GENERATING_REQUIREMENTS"
    DONE = "DONE"
    CANCELLED = "CANCELLED"
    ERROR = "ERROR"
