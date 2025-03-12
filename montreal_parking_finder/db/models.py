"""
Database models for storing parking data.
"""

from sqlalchemy import (
    Column, Integer, Float, String, Boolean, 
    ForeignKey, DateTime, JSON, Text, create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import json

from montreal_parking_finder.config import DB_URI

Base = declarative_base()


class ParkingSign(Base):
    """
    Model representing a parking sign.
    """
    __tablename__ = 'parking_signs'
    
    id = Column(Integer, primary_key=True)
    sign_id = Column(String(50), unique=True, index=True)  # ID_PANNEAU from dataset
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    description = Column(Text)
    arrow_direction = Column(String(20))  # 'left', 'right', 'both_sides', 'up'
    is_restricted = Column(Boolean, default=False)
    is_all_time = Column(Boolean, default=False)
    is_paid = Column(Boolean, default=False)
    
    # JSON serialized restriction data
    raw_restriction = Column(JSON)
    
    # Relationships
    intervals = relationship("ParkingInterval", back_populates="sign", cascade="all, delete-orphan")
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<ParkingSign(id={self.id}, lat={self.latitude}, lon={self.longitude})>"
    
    @classmethod
    def from_dataframe_row(cls, row):
        """
        Create a ParkingSign from a DataFrame row.
        """
        return cls(
            sign_id=str(row.get('ID_PANNEAU', '')),
            latitude=row['Latitude'],
            longitude=row['Longitude'],
            description=row.get('DESCRIPTION_RPA', ''),
            arrow_direction=row.get('arrow_direction', 'both_sides'),
            is_restricted=row.get('is_restricted', False),
            is_all_time=row.get('is_all_time', False),
            is_paid=row.get('is_paid', False),
            raw_restriction=json.dumps(row.get('parsed_restriction', {}))
        )


class ParkingInterval(Base):
    """
    Model representing a parking interval along a street.
    """
    __tablename__ = 'parking_intervals'
    
    id = Column(Integer, primary_key=True)
    sign_id = Column(Integer, ForeignKey('parking_signs.id'))
    street_name = Column(String(255))
    
    # Serialized LineString geometry for the interval
    geometry = Column(Text)
    
    # Start and end points of the interval
    start_lat = Column(Float)
    start_lon = Column(Float)
    end_lat = Column(Float)
    end_lon = Column(Float)
    
    # Relationships
    sign = relationship("ParkingSign", back_populates="intervals")
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f"<ParkingInterval(id={self.id}, street={self.street_name})>"


class CachedStreetData(Base):
    """
    Model for caching street data to reduce API calls.
    """
    __tablename__ = 'cached_streets'
    
    id = Column(Integer, primary_key=True)
    latitude = Column(Float)
    longitude = Column(Float)
    radius = Column(Integer)
    
    # Street data
    street_id = Column(String(50))
    street_name = Column(String(255))
    highway_type = Column(String(50))
    
    # Serialized geometry
    geometry = Column(Text)
    
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f"<CachedStreetData(lat={self.latitude}, lon={self.longitude}, street={self.street_name})>"


class AreaSummary(Base):
    """
    Model for storing summaries of analyzed areas.
    """
    __tablename__ = 'area_summaries'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    center_lat = Column(Float)
    center_lon = Column(Float)
    radius_km = Column(Float)
    
    total_signs = Column(Integer)
    total_intervals = Column(Integer)
    free_intervals = Column(Integer)
    restricted_intervals = Column(Integer)
    
    last_analyzed = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f"<AreaSummary(name={self.name}, center=({self.center_lat}, {self.center_lon}))>"


# Database initialization functions
def init_db():
    """
    Initialize the database and create tables.
    """
    engine = create_engine(DB_URI)
    Base.metadata.create_all(engine)
    return engine


def get_session():
    """
    Get a database session.
    """
    engine = create_engine(DB_URI)
    Session = sessionmaker(bind=engine)
    return Session()
