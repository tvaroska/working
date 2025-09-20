"""
Application configuration model for storing global settings
"""

from sqlalchemy import Column, String, JSON, DateTime
from sqlalchemy.sql import func
from ..database import Base


class AppConfig(Base):
    """
    Application configuration database model.
    
    Stores global application settings as key-value pairs in the database.
    Allows for dynamic configuration changes without requiring application
    restarts. Values are stored as JSON for flexibility.
    
    Attributes:
        key: Configuration key (primary key)
        value: Configuration value stored as JSON
        updated_at: Timestamp of last configuration update
        
    Example keys:
        - 'user_preferences': User interface preferences
        - 'ai_settings': AI processing configuration
        - 'content_filters': Content filtering rules
        - 'notification_settings': Notification preferences
    """
    
    __tablename__ = "app_config"
    
    key = Column(String(100), primary_key=True)
    value = Column(JSON, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        """
        String representation of AppConfig instance.
        
        Returns:
            str: Human-readable representation showing key and value
        """
        return f"<AppConfig(key='{self.key}', value={self.value})>"