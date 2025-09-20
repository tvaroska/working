"""
App configuration Pydantic schemas
"""

from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime


class AppConfigUpdate(BaseModel):
    """Schema for updating app configuration"""
    value: Dict[str, Any]


class AppConfigResponse(BaseModel):
    """Schema for app configuration response"""
    key: str
    value: Dict[str, Any]
    updated_at: datetime
    
    class Config:
        from_attributes = True