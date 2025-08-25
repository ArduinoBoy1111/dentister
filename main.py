import os
import sys
import urllib.parse
import webview
from datetime import datetime
import subprocess
from database import Base, engine, SessionLocal 
from models import Patient, Transfer 
from sqlalchemy import desc

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

    # --- Transfers ---
    def submitForm_T(self, data):
        data = dict(data)
        name = data.get("name")
        phone_num = data.get("phone_num")
        clinic_name = data.get("clinic_name")
        transfer_type = data.get("transfer_type") == 1
        date_obj = datetime.strptime(data.get("date"), "%Y-%m-%d").date()
        
        db = SessionLocal()
        transfer = Transfer(
            name=name,
            phone_num=phone_num,
            clinic_name=clinic_name,
            date=date_obj,
            transfer_type=transfer_type,
            
        )
        db.add(transfer)
        db.commit()
        db.refresh(transfer)
        db.close()

    def get_transfers(self):
        db = SessionLocal()
        transfers = db.query(Transfer).all()
        db.close()

        return [
            {
                "id": t.id,
                "name": t.name,
                "phone_num": t.phone_num,
                "date": t.date.isoformat(),
                "clinic_name": t.clinic_name,
                "transfer_type": t.transfer_type,
            }
            for t in transfers
        ]

    def deleteTransfer(self, id):
        db = SessionLocal()
        db.query(Transfer).filter(Transfer.id == int(id)).delete()
        db.commit()
        db.close()

    def deleteTransfers(self, date, type):
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        db = SessionLocal()
        db.query(Transfer).filter(
            Transfer.date == date_obj, Transfer.transfer_type == (type == 1)
        ).delete()
        db.commit()
        db.close()

    def editTransfer(self, id, data):
        data = dict(data)
        date_obj = datetime.strptime(data.get("date"), "%Y-%m-%d").date()

        db = SessionLocal()
        transfer = db.query(Transfer).filter(Transfer.id == id).first()
        if transfer:
            transfer.name = data.get("name", transfer.name)
            transfer.phone_num = data.get("phone_num", transfer.phone_num)
            transfer.clinic_name = data.get("clinic_name", transfer.clinic_name)
            transfer.date = date_obj
            db.commit()
            db.refresh(transfer)
        db.close()
    
    
    
def on_loaded():
    # This will maximize the window after creation
    webview.windows[0].maximize()

# --- Start app ---
api = API()
window = webview.create_window("Dentister", load_page("index"), js_api=api,resizable=False)
webview.start(on_loaded)
