import os
import sys
import urllib.parse
import webview
from datetime import datetime
import subprocess
from database import Base, engine, SessionLocal 
from models import Patient, Transfer ,User
from sqlalchemy import desc
from sqlalchemy.orm import joinedload

# --- Database setup ---
Base.metadata.create_all(bind=engine)




# --- Path helpers ---
def resource_path(relative_path):
    """Get absolute path to resource (works in dev and in PyInstaller exe)."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def get_url(relative_path):
    abs_path = resource_path(relative_path)
    return f"file:///{urllib.parse.quote(abs_path.replace(os.sep, '/'))}"


def load_page(name):
    if name == "index":
        return get_url("assets/index.html")
    elif name == "second":
        return get_url("assets/sendnreceive.html")
    elif name == "search":
        return get_url("assets/search.html")
    return get_url("assets/404.html")


# --- API for JS ---
class API:
    def navigate(self, page_name):
        url = load_page(page_name)
        window.load_url(url)

    def call_number(self, phone_number):
        if phone_number:
            num = "+964" + phone_number[1:]

            # Run ADB without opening a console window
            startupinfo = None
            if os.name == "nt":  # Windows
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            subprocess.run(
                ["adb", "shell", "am", "start", "-a", "android.intent.action.CALL", "-d", f"tel:{num}"],
                startupinfo=startupinfo
            )
    # --- Patients ---
    def submitForm(self, data,time):
        data = dict(data)
        name = data.get("name")
        phone_num = data.get("phone_num")
        info = data.get("info")
        date_obj = datetime.strptime(data.get("date"), "%Y-%m-%d").date()

        
        db = SessionLocal()
        patient = Patient(name=name, phone_num=phone_num, info=info, date=date_obj,time=time)
        db.add(patient)
        db.commit()
        db.refresh(patient)
        db.close()

    def deletePatient(self, id):
        db = SessionLocal()
        db.query(Patient).filter(Patient.id == int(id)).delete()
        db.commit()
        db.close()

    def deletePatients(self, date):
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        db = SessionLocal()
        db.query(Patient).filter(Patient.date == date_obj).delete()
        db.commit()
        db.close()

    def get_patients(self):
        db = SessionLocal()
        patients = db.query(Patient).order_by(desc(Patient.time))
        db.close()

        return [
            {
                "id": p.id,
                "name": p.name,
                "phone_num": p.phone_num,
                "date": p.date.isoformat(),
                "info": p.info,
                "time":p.time
            }
            for p in patients
        ]

    def editPatient(self, id, data):
        data = dict(data)
        date_obj = datetime.strptime(data.get("date"), "%Y-%m-%d").date()

        db = SessionLocal()
        patient = db.query(Patient).filter(Patient.id == id).first()
        if patient:
            patient.name = data.get("name", patient.name)
            patient.phone_num = data.get("phone_num", patient.phone_num)
            patient.info = data.get("info", patient.info)
            patient.date = date_obj
            db.commit()
            db.refresh(patient)
        db.close()


    def createUser(self, data):
        data = dict(data)
        name = data.get("name")
        phone_num = data.get("phone_num")
        treat_type = data.get("treat_type")
        
        db = SessionLocal()
        new_user = User(name=name, phone_num=phone_num, treat_type=treat_type)

        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        print(f"user created: {new_user.id} {new_user.name}")
        db.close()
        
    def createTransfer(self, data, id):
        data = dict(data)
        transfer_type = data.get("transfer_type")
        teeth_num = data.get("teeth_num")
        date = data.get("date")
        clinic_name = data.get("clinic_name")
        
        db = SessionLocal()
        new_transfer = Transfer(
            transfer_type=transfer_type,
            teeth_num=teeth_num,
            date=datetime.strptime(data.get("date"), "%Y-%m-%d").date(),
            clinic_name=clinic_name
        )

        user = db.query(User).filter_by(id=id).first()
        user.transfers.append(new_transfer)
        
        db.commit()
        db.refresh(new_transfer)
        db.close()
        
    def getUsers(self):
        db = SessionLocal()
        users = db.query(User).options(joinedload(User.transfers)).all()
        db.close()

        return [
            {
                "id": p.id,
                "name": p.name,
                "phone_num": p.phone_num,
                "done": p.done,
                "treat_type": p.treat_type,
                "transfers": [
                    {
                        "id": t.id,
                        "transfer_type": t.transfer_type,
                        "teeth_num": t.teeth_num,
                        "date": t.date.isoformat(),
                        "clinic_name": t.clinic_name
                    } for t in p.transfers
                ]
            }
            for p in users
        ]
        
        
    
def on_loaded():
    # This will maximize the window after creation
    webview.windows[0].maximize()

# --- Start app ---
api = API()
window = webview.create_window("Dentister", load_page("index"), js_api=api,resizable=False)
webview.start(on_loaded)
