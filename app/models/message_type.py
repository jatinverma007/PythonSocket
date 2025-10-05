from enum import Enum

class MessageType(str, Enum):
    """Enum for different message types"""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    TEXT_WITH_IMAGE = "text_with_image"
    TEXT_WITH_VIDEO = "text_with_video"
    TEXT_WITH_AUDIO = "text_with_audio"
    TEXT_WITH_DOCUMENT = "text_with_document"
