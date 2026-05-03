from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_history.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String, default="operator") # operator, manager, client
    projects = relationship("Project", back_populates="owner")
    tests = relationship("TestRecord", back_populates="user")

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    owner = relationship("User", back_populates="projects")
    tests = relationship("TestRecord", back_populates="project")

class TestRecord(Base):
    __tablename__ = "test_records"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    project_name = Column(String, index=True) # Legacy
    operator = Column(String) # Legacy
    specimen_id = Column(String)
    filename = Column(String)
    
    fc = Column(Float)
    e_modulus = Column(Float)
    eps0 = Column(Float)
    eps_u = Column(Float)
    
    toughness = Column(Float, nullable=True)
    age_days = Column(Integer, nullable=True)
    fc_28_pred = Column(Float, nullable=True)
    compliance_status = Column(String, nullable=True)
    anomaly_flag = Column(Boolean, default=False)
    image_path = Column(String, nullable=True)
    
    project = relationship("Project", back_populates="tests")
    user = relationship("User", back_populates="tests")
