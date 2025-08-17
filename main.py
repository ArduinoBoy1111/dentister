import os
import webview
import urllib.parse
from database import Base, engine , SessionLocal
from models import Patient , Transfer
from datetime import datetime

Base.metadata.create_all(bind=engine)

def get_url(relative_path):
    abs_path = os.path.abspath(relative_path)
    return f"file:///{urllib.parse.quote(abs_path.replace(os.sep, '/'))}"

def load_page(name):
    if name == "index":
        return get_url("assets/index.html")
    elif name == "second":
        return get_url("assets/sendnreceive.html")
    elif name == "settings":
        return get_url("assets/settings.html")
    
    return get_url("assets/404.html")

class API:
    
    def navigate(self, page_name):
        url = load_page(page_name)
        window.load_url(url)
    # first page methods
    def submitForm(self,data):
        
        data = dict(data)
        name = data.get("name")
        phone_num = data.get("phone_num")
        info = data.get("info")
        date_str = data.get("date")
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        print(name , phone_num , info , date_obj)
        
        db = SessionLocal()
        patient =  Patient(name=name,phone_num=phone_num,info=info,date=date_obj)
        db.add(patient)
        db.commit()
        db.refresh(patient)
        
        db.close()
    
    def deletePatient(self,id):
        id = int(id)
        db = SessionLocal()
        db.query(Patient).filter(Patient.id == int(id)).delete()
        db.commit()
        db.close()
        
    def deletePatients(self,date):
        print(f"Python deletePatients received date: {date}")
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        db = SessionLocal()
        db.query(Patient).filter(Patient.date == date_obj).delete()
        db.commit()
        db.close()
        
    def get_patients(self):
        db = SessionLocal()
        patients = db.query(Patient).all()
        db.close()
        
        result = []
        for p in patients:
            result.append({
                "id": p.id,
                "name": p.name,
                "phone_num": p.phone_num,
                "date": p.date.isoformat(),  # convert date to string
                "info": p.info
            })
        return result
        
    def editPatient(self,id,data):
        data = dict(data)
        name = data.get("name")
        phone_num = data.get("phone_num")
        info = data.get("info")
        date_str = data.get("date")
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        print(name , phone_num , info , date_obj)
        
        db = SessionLocal()
        patient =  db.query(Patient).filter(Patient.id == id).first()
        if patient:
            if name is not None:
                patient.name = name
            if phone_num is not None:
                patient.phone_num = phone_num
            if info is not None:
                patient.info = info
            if date_obj is not None:
                patient.date = date_obj
            
        db.commit()
        db.refresh(patient)
        db.close()
        
    # second page methods
    def submitForm_T(self,data):
    
        data = dict(data)
        name = data.get("name")
        phone_num = data.get("phone_num")
        clinic_name = data.get("clinic_name")
        date_str = data.get("date")
        transfer_type = data.get("transfer_type")=="1"
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        print(name , phone_num , clinic_name , date_obj)
        
        db = SessionLocal()
        transfer =  Transfer(name=name,phone_num=phone_num,clinic_name=clinic_name,date=date_obj,transfer_type=transfer_type)
        db.add(transfer)
        db.commit()
        db.refresh(transfer)
        
        db.close()

    def get_transfers(self):
        db = SessionLocal()
        transfers = db.query(Transfer).all()
        db.close()
        
        result = []
        for t in transfers:
            result.append({
                "id": t.id,
                "name": t.name,
                "phone_num": t.phone_num,
                "date": t.date.isoformat(),  # convert date to string
                "clinic_name": t.clinic_name,
                "transfer_type": t.transfer_type
            })
        return result

    def deleteTransfer(self,id):
        id = int(id)
        db = SessionLocal()
        db.query(Transfer).filter(Transfer.id == int(id)).delete()
        db.commit()
        db.close()
        
    def deleteTransfers(self,date,type):
        print(f"Python deletePatients received date: {date}")
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        db = SessionLocal()
        db.query(Transfer).filter(Transfer.date == date_obj,Transfer.transfer_type == (type==1)).delete()
        db.commit()
        db.close()
    
    def editTransfer(self,id,data):
        data = dict(data)
        name = data.get("name")
        phone_num = data.get("phone_num")
        info = data.get("info")
        date_str = data.get("date")
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        print(name , phone_num , info , date_obj)
        
        db = SessionLocal()
        transfer =  db.query(Transfer).filter(Transfer.id == id).first()
        if transfer:
            if name is not None:
                transfer.name = name
            if phone_num is not None:
                transfer.phone_num = phone_num
            if info is not None:
                transfer.info = info
            if date_obj is not None:
                transfer.date = date_obj
            
        db.commit()
        db.refresh(transfer)
        db.close()
      

api = API()
window = webview.create_window("Dentister", load_page("index"), js_api=api)
webview.start()
