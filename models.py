from sqlalchemy import Column, Integer, String ,Date,Boolean,ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Patient(Base):
    __tablename__ = "patients"
    
    # general features
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    doctor = Column(String, nullable=False,default="0")
    phone_num = Column(String, nullable=False)
    creation_date = Column(Date,nullable=False)
    
    # meetings features
    meetings = relationship(
        "Meeting",
        back_populates="patient",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    
    # transfers features
    transfers = relationship(
        "Transfer",
        back_populates="patient",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    treat_type = Column(String, nullable=False,default="none")
    transfer_state = Column(Boolean, nullable=False,default=False) # is it done ?
    
    # implant features 
    implant_total = Column(Integer,default=0)
    implant_current = Column(Integer,default=0)
    implant_state = Column(Boolean, nullable=False,default=False)
   
   
   
   
    
class Meeting(Base):
    __tablename__ = "meetings"
    id = Column(Integer, primary_key=True, index=True)
    
    meeting_type = Column(String,nullable=False,default="general")
    info = Column(String,nullable=True)
    date = Column(Date,nullable=False)
    time = Column(Boolean, nullable=False,default=False)
    
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    patient = relationship("Patient", back_populates="meetings")
    
class Transfer(Base):
    __tablename__ = "transfers"
    id = Column(Integer, primary_key=True, index=True)
    
    transfer_type = Column(Boolean,nullable=False)
    date = Column(Date,nullable=False)
    clinic_name = Column(String)
    
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    patient = relationship("Patient", back_populates="transfers")

