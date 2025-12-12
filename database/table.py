from database.connection import Base, engine
from sqlalchemy import Column, DateTime, DECIMAL, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid


class Servers(Base):
    __tablename__ = "servers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    vm = Column(String, nullable=False)

    # Date column with proper data type
    date = Column(String) # DateTime(timezone=True)
    # OR if you want it to auto-set on creation:
    # date = Column(DateTime(timezone=True), server_default=func.now())

    metric = Column(String)
    max_value = Column(DECIMAL(10, 2))
    min_value = Column(DECIMAL(10, 2))
    avg_value = Column(DECIMAL(10, 2))

    created_at = Column(DateTime(timezone=True), server_default=func.now())