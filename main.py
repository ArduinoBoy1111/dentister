import os
import sys
import urllib.parse
import webview
from datetime import datetime
import subprocess
from database import Base, engine, SessionLocal 
from models import Patient, Transfer,Meeting
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
    def createPatient(self, data):
        data = dict(data)
        name = data.get("name")
        phone_num = data.get("phone_num")
        doctor = data.get("doctor")

        db = SessionLocal()
        patient = Patient(name=name, phone_num=phone_num, doctor=doctor)
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


    def createMeeting(self,data,id):
        data = dict(data)
        #meeting_type = meeting_type
        info = data.get("info")
        date_obj = data.get("date")
        time = data.get("time")
        
        db = SessionLocal()
        new_meeting = Meeting(info=info, date=datetime.strptime(date_obj, "%Y-%m-%d").date(), time=time)

        patient = db.query(Patient).filter_by(id=id).first()
        patient.meetings.append(new_meeting)
        
        db.commit()
        db.refresh(new_meeting)
        db.close()
        
    def createTransfer(self,transfer_type, data, id):
        data = dict(data)
        transfer_type = transfer_type=="1"
        date_obj = data.get("date")
        clinic_name = data.get("clinic_name")
        
        db = SessionLocal()
        new_transfer = Transfer(
            transfer_type=transfer_type,
            date=datetime.strptime(date_obj, "%Y-%m-%d").date(),
            clinic_name=clinic_name
        )

        patient = db.query(Patient).filter_by(id=id).first()
        patient.transfers.append(new_transfer)
        
        db.commit()
        db.refresh(new_transfer)
        db.close()
        

    def get_meetings(self):
            db = SessionLocal()
            rows = (db.query(Meeting).options(joinedload(Meeting.patient)).all())
            db.close()
            return [
                {
                    "id": m.id,
                    "meeting_type": m.meeting_type,
                    "info": m.info,
                    "date": m.date.isoformat(),
                    "time": m.time,
                    "patient": {
                        "id": m.patient.id,
                        "name": m.patient.name,
                        "doctor": m.patient.doctor,
                        "phone_num": m.patient.phone_num,
                        "treat_type": m.patient.treat_type,
                        "transfer_state": m.patient.transfer_state,
                        "implant_total": m.patient.implant_total or 0,
                        "implant_current": m.patient.implant_current or 0,
                        "implant_state": m.patient.implant_state,
                    },
                }
                for m in rows
                ]
        
    
        
    
def on_loaded():
    # This will maximize the window after creation
    webview.windows[0].maximize()

# --- Start app ---

api = API()
window = webview.create_window("Dentister", load_page("index"), js_api=api,resizable=False)
webview.start(on_loaded)
