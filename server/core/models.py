"""
VaultMind 2.0 - Persistence Layer (Models)
Defines the WORM (Write Once Read Many) compatible database schema
for storing fraud alerts securely using SQLAlchemy.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import declarative_base

# Base declarative class for SQLAlchemy models
Base = declarative_base()

class FraudAlert(Base):
    """
    FraudAlert Model
    Represents an immutable, tamper-evident record of a detected anomaly.
    Uses cryptographic hashes to link records in a blockchain-like structure.
    """
    __tablename__ = 'alerts'

    # 1. Core Fields
    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String(255), nullable=False, index=True)
    emp_id = Column(String(255), nullable=False, index=True)
    risk_score = Column(Integer, nullable=False)
    action_type = Column(String(255), nullable=False)
    # Storing complex structures like reasons as JSON string text
    detection_reasons = Column(Text, nullable=True) 

    # 2. Cryptographic Ledger Fields
    block_id = Column(Integer, nullable=False, unique=True)
    data_hash_sha256 = Column(String(64), nullable=False)
    block_hash_sha256 = Column(String(64), nullable=False)
    previous_hash = Column(String(64), nullable=False)

    # 3. Compliance & Audit Fields
    # Default is PENDING. Accepts CONFIRMED or DISMISSED for soft-deletions / WORM compliance.
    # Note: No hard DELETE cascading relationships exist in this schema to satisfy compliance.
    auditor_status = Column(String(50), default="PENDING", nullable=False)
    is_tampered = Column(Boolean, default=False, nullable=False)
    retention_expiry_date = Column(DateTime, nullable=False)
