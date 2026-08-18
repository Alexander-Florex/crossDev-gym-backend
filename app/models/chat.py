import uuid
from enum import StrEnum

from sqlalchemy import BigInteger, Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import SoftDeleteMixin, TenantMixin, TimestampMixin, UUIDPKMixin


class ConversationStatus(StrEnum):
    open = "open"
    closed = "closed"


class ParticipantRole(StrEnum):
    trainer = "trainer"
    student = "student"


class MessageType(StrEnum):
    text = "text"
    image = "image"
    file = "file"


class Conversation(UUIDPKMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "conversations"

    assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trainer_student_assignments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[ConversationStatus] = mapped_column(
        default=ConversationStatus.open, nullable=False
    )


class ConversationParticipant(UUIDPKMixin, Base):
    __tablename__ = "conversation_participants"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[ParticipantRole] = mapped_column(nullable=False)


class Message(UUIDPKMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[MessageType] = mapped_column(default=MessageType.text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Attachment(UUIDPKMixin, Base):
    __tablename__ = "attachments"

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
