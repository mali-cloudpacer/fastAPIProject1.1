from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base



Base = declarative_base()

# Define the Database Models
class Employee(Base):
    __tablename__ = 'employees'
    id = Column(Integer, primary_key=True)
    age = Column(Integer)
    gender = Column(String)
    marital_status = Column(String)
    department_id = Column(Integer, ForeignKey("departments.id"))
    department = relationship("Department", back_populates="employees")
    job_info_id = Column(Integer, ForeignKey("job_infos.id"))
    job_info = relationship("JobInfo", back_populates="employees")
    performance_info_id = Column(Integer, ForeignKey("performance_infos.id"))
    performance_info = relationship("PerformanceInfo", back_populates="employees")


class Department(Base):
    __tablename__ = 'departments'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    employees = relationship("Employee", back_populates="department")


class JobInfo(Base):
    __tablename__ = 'job_infos'
    id = Column(Integer, primary_key=True)
    job_role = Column(String)
    job_level = Column(Integer)
    years_at_company = Column(Integer)
    employees = relationship("Employee", back_populates="job_info")


class PerformanceInfo(Base):
    __tablename__ = 'performance_infos'
    id = Column(Integer, primary_key=True)
    attrition = Column(Boolean)
    performance_rating = Column(Integer)
    percent_salary_hike = Column(Float)
    employees = relationship("Employee", back_populates="performance_info")
