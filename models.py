from sqlalchemy import Column, Integer, String ,Date,Boolean,ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone_num = Column(String, nullable=False)
    date = Column(Date,nullable=False)
    info = Column(String)
    time = Column(Boolean,nullable=False)
    
    
class User(Base):
    __tablename__ = "users"    
    id = Column(Integer, primary_key=True)
    
    name = Column(String, nullable=False)
    phone_num = Column(String, nullable=False)
    done = Column(Boolean, nullable=False,default=False)
    treat_type = Column(String, nullable=False)
    
    transfers = relationship(
    "Transfer",
    back_populates="user",
    cascade="all, delete-orphan",
    passive_deletes=True
)

    
class Transfer(Base):
    __tablename__ = "transfers"
    id = Column(Integer, primary_key=True, index=True)
    
    transfer_type = Column(Boolean,nullable=False)
    teeth_num = Column(Integer, nullable=False)
    date = Column(Date,nullable=False)
    clinic_name = Column(String)
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user = relationship("User", back_populates="transfers")
