from database.connection import Base, engine
from sqlalchemy import Column, DateTime, DECIMAL, String, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid


class ServerMetrics(Base):
    """
    Модель для хранения метрик серверов
    Соответствующая таблице server_metrics в PostgreSQL
    """
    __tablename__ = "server_metrics"

    __table_args__ = (
        UniqueConstraint('vm', 'date', 'metric', name='uq_vm_date_metric'),
        Index('idx_metrics_vm_date', 'vm', 'date', 'metric'),
        Index('idx_metrics_date', 'date'),
        Index('idx_metrics_metric', 'metric'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    vm = Column(String(255), nullable=False, index=True)
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    metric = Column(String(100), nullable=False, index=True)
    max_value = Column(DECIMAL(10, 5), nullable=True)
    min_value = Column(DECIMAL(10, 5), nullable=True)
    avg_value = Column(DECIMAL(10, 5), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<ServerMetrics(vm='{self.vm}', date='{self.date}', metric='{self.metric}', avg_value={self.avg_value})>"


# Обратная совместимость
Servers = ServerMetrics
