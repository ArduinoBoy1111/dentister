from sqlalchemy import Column, Integer, String ,Date,Boolean
from database import Base

class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone_num = Column(String, nullable=False)
    date = Column(Date,nullable=False)
    info = Column(String)
    time = Column(Boolean,nullable=False)
    
class Transfer(Base):
    __tablename__ = "transfers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    transfer_type = Column(Boolean,nullable=False)
    phone_num = Column(String, nullable=False)
    date = Column(Date,nullable=False)
    clinic_name = Column(String)