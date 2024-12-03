import uuid

from sqlalchemy import text, types
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass, Mapped, mapped_column

class Base(MappedAsDataclass, DeclarativeBase):
    pass

class Documents(Base):
    __tablename__ = 'documents'

    id : Mapped[uuid.UUID] = mapped_column(types.Uuid,
        primary_key=True,
        init=False,
        server_default=text("gen_random_uuid()"))
    content : Mapped[str]

