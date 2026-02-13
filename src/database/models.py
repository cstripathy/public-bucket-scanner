"""Database models for bucket scanner."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class ScanResult(Base):
    """Model for storing scan results."""
    
    __tablename__ = "scan_results"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    bucket_name = Column(String(255), index=True, nullable=False)
    provider = Column(String(50), index=True, nullable=False)
    
    # Status fields
    exists = Column(Boolean, default=False)
    is_accessible = Column(Boolean, default=False)
    access_level = Column(String(50))
    
    # Details
    url = Column(String(500))
    permissions = Column(JSON)  # List of permissions
    files_found = Column(JSON)  # List of files
    sensitive_files = Column(JSON)  # List of sensitive files
    
    # Risk assessment
    risk_level = Column(String(20))  # low, medium, high, critical
    risk_score = Column(Integer, default=0)
    
    # Metadata
    error = Column(Text)
    extra_data = Column(JSON)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def to_dict(self):
        """Convert model to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            'id': self.id,
            'bucket_name': self.bucket_name,
            'provider': self.provider,
            'exists': self.exists,
            'is_accessible': self.is_accessible,
            'access_level': self.access_level,
            'url': self.url,
            'permissions': self.permissions,
            'files_found': self.files_found,
            'sensitive_files': self.sensitive_files,
            'risk_level': self.risk_level,
            'risk_score': self.risk_score,
            'error': self.error,
            'extra_data': self.extra_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ScanTask(Base):
    """Model for scan tasks/queue."""
    
    __tablename__ = "scan_tasks"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    bucket_name = Column(String(255), index=True, nullable=False)
    provider = Column(String(50))  # null = all providers
    
    # Status
    status = Column(String(20), default='pending', index=True)  # pending, processing, completed, failed
    priority = Column(Integer, default=0, index=True)
    
    # Results
    result_count = Column(Integer, default=0)
    error = Column(Text)

    # Metadata
    extra_data = Column(JSON)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'bucket_name': self.bucket_name,
            'provider': self.provider,
            'status': self.status,
            'priority': self.priority,
            'result_count': self.result_count,
            'error': self.error,
            'extra_data': self.extra_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }


class Finding(Base):
    """Model for security findings."""
    
    __tablename__ = "findings"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    scan_result_id = Column(Integer, index=True)
    
    bucket_name = Column(String(255), index=True, nullable=False)
    provider = Column(String(50), index=True)
    
    # Finding details
    finding_type = Column(String(100), index=True)  # public_bucket, sensitive_file, etc.
    severity = Column(String(20), index=True)  # low, medium, high, critical
    title = Column(String(500))
    description = Column(Text)
    
    # Location
    file_path = Column(String(1000))
    url = Column(String(500))
    
    # Recommendations
    recommendations = Column(JSON)
    
    # Status
    status = Column(String(20), default='open', index=True)  # open, acknowledged, resolved, false_positive
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True))
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'scan_result_id': self.scan_result_id,
            'bucket_name': self.bucket_name,
            'provider': self.provider,
            'finding_type': self.finding_type,
            'severity': self.severity,
            'title': self.title,
            'description': self.description,
            'file_path': self.file_path,
            'url': self.url,
            'recommendations': self.recommendations,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
        }
