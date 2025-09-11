import os
import sys
import urllib.parse
import webview
from datetime import datetime, date, timedelta
import subprocess
from database import Base, engine, SessionLocal 
from models import Patient, Transfer, Meeting
from sqlalchemy import desc
from sqlalchemy.orm import joinedload
import random

# --- Database setup ---
Base.metadata.create_all(bind=engine)

current_patient_id = 1
page_to_load = 0
current_doctor = "0"

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
    elif name == "implant":
        return get_url("assets/implant.html")
    elif name == "braces":
        return get_url("assets/braces.html")
    elif name == "second":
        return get_url("assets/sendnreceive.html")
    elif name == "search":
        return get_url("assets/search.html")
    elif name == "patient":
        return get_url("assets/patient.html")
    return get_url("assets/404.html")

# --- small sort helpers (keep ordering consistent everywhere) ---
def _sort_meetings(iterable):
    # newest date first, then time (1 before 0), then newest id
    return sorted(iterable, key=lambda m: (m.date, m.time, m.id), reverse=True)

def _sort_transfers(iterable):
    # newest date first, then newest id
    return sorted(iterable, key=lambda t: (t.date, t.id), reverse=True)

def _sort_payments(iterable):
    # newest date first, then newest id
    return sorted(iterable, key=lambda p: (p.date, p.id), reverse=True)

def _apply_doctor_filter(q):
    if current_doctor and current_doctor != "-1":
        return q.filter(Patient.doctor.isnot(None)).filter(Patient.doctor.contains(current_doctor))
    return q

# --- API for JS ---
class API:
    def navigate(self, page_name):
        url = load_page(page_name)
        window.load_url(url)
        print(f"Navigated to {page_name}")

    def call_number(self, phone_number):
        if phone_number:
            num = "+964" + phone_number[1:]

            # Run ADB without opening a console window
            startupinfo = None
            if os.name == "nt":  # Windows
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            subprocess.run(
                ["adb", "shell", "am", "start", "-a", "android.intent.action.DIAL", "-d", f"tel:{num}"],
                startupinfo=startupinfo
            )

    # --- Patients ---
    def createPatient(self, data):
        data = dict(data)
        name = data.get("name")
        phone_num = data.get("phone_num")
        doctor = data.get("doctor")


        db = SessionLocal()
        patient = Patient(
            name=name,
            phone_num=phone_num,
            doctor=doctor,
            creation_date=date.today(),
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
        db.close()
        
    def createTransferPatient(self, data):
        data = dict(data)
        name = data.get("name")
        phone_num = data.get("phone_num")
        doctor = data.get("doctor")
        treat_type = data.get("treat_type")

        db = SessionLocal()
        patient = Patient(
            name=name,
            phone_num=phone_num,
            doctor=doctor,
            creation_date=date.today(),
            treat_type=treat_type
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
        db.close()

        print("Created Transfer patient:", patient.id, patient.name)

    def get_patients(self):
        db = SessionLocal()
        try:
            q = db.query(Patient)
            q = _apply_doctor_filter(q)
            rows = q.order_by(desc(Patient.creation_date)).all()
            return [
                {
                    "id": p.id,
                    "name": p.name,
                    "doctor": p.doctor,
                    "phone_num": p.phone_num,
                    "treat_type": p.treat_type,
                    "transfer_state": p.transfer_state,
                    "transfers": [
                        {
                            "id": t.id,
                            "transfer_type": t.transfer_type,
                            "date": t.date.isoformat() if t.date else None,
                            "clinic_name": t.clinic_name,
                        }
                        for t in _sort_transfers(p.transfers)
                    ],
                }
                for p in rows
            ]
        finally:
            db.close()

   

    def editPatient(self, data, pid):
        data = dict(data)
        name = data.get("name")
        phone_num = data.get("phone_num")
        treat_type = data.get("treat_type")
        doctor = data.get("doctor")

        db = SessionLocal()
        patient = db.query(Patient).filter(Patient.id == pid).first()
        if not patient:
            db.close()
            return None

        patient.name = name
        patient.phone_num = phone_num
        patient.doctor = doctor
        if treat_type and treat_type != "":
            patient.treat_type = treat_type



        db.commit()
        db.refresh(patient)
        db.close()

    def deletePatient(self, pid):
        db = SessionLocal()
        # Delete all meetings for this patient
        db.query(Meeting).filter(Meeting.patient_id == int(pid)).delete()
        # Delete all transfers for this patient
        db.query(Transfer).filter(Transfer.patient_id == int(pid)).delete()
        # Delete the patient itself
        db.query(Patient).filter(Patient.id == int(pid)).delete()
        db.commit()
        db.close()
        
    def deleteMeeting(self, id):
        db = SessionLocal()
        db.query(Meeting).filter(Meeting.id == int(id)).delete()
        db.commit()
        db.close()

    def deleteMeetings(self, date):
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        db = SessionLocal()
        db.query(Meeting).filter(Meeting.date == date_obj).delete()
        db.commit()
        db.close()

    def createMeeting(self, data, time, id, meeting_type="general"):
        data = dict(data)
        meeting_type_2 = data.get("meeting_type_2")
        info = data.get("info")
        date_obj = data.get("date")
        meeting_type = meeting_type

        db = SessionLocal()
        new_meeting = Meeting(
            info=info,
            date=datetime.strptime(date_obj, "%Y-%m-%d").date(),
            time=time,
            meeting_type=meeting_type,
            meeting_type_2=meeting_type_2
        )

        patient = db.query(Patient).filter_by(id=id).first()
        patient.meetings.append(new_meeting)

        if id:
            patient = db.query(Patient).filter_by(id=id).first()
            patient.meetings.append(new_meeting)


        db.commit()
        db.refresh(new_meeting)
        db.close()

    def editMeeting(self, meeting_id, data, time, patient_id):
        data = dict(data)
        info = data.get("info")
        meeting_type_2 = data.get("meeting_type_2")
        date_str = data.get("date")
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()

        db = SessionLocal()
        meeting = db.query(Meeting).filter_by(id=meeting_id).first()
        if not meeting:
            db.close()
            return None

        # Update fields
        meeting.meeting_type_2 = meeting_type_2
        meeting.info = info
        meeting.date = date_obj
        meeting.time = time

        # (Optional) Re-assign to a different patient
        if patient_id:
            patient = db.query(Patient).filter_by(id=patient_id).first()
            if patient:
                meeting.patient = patient

        db.commit()
        db.refresh(meeting)
        db.close()

    def createTransfer(self, transfer_type, data, id):
        data = dict(data)
        transfer_type = transfer_type == "1"
        date_obj = data.get("date")
        clinic_name = data.get("clinic_name")

        db = SessionLocal()
        new_transfer = Transfer(
            transfer_type=transfer_type,
            date=datetime.strptime(date_obj, "%Y-%m-%d").date(),
            clinic_name=clinic_name,
        )
        
        # change the pat treat_type if it's none
        if id:
            patient = db.query(Patient).filter_by(id=id).first()
            patient.transfers.append(new_transfer)
            if patient.treat_type == "none":
                treat_type = data.get("treat_type")
                if treat_type:
                    patient.treat_type = treat_type
        
        db.commit()
        db.refresh(new_transfer)
        db.refresh(patient)
        db.close()

    def deleteTransfer(self, transfer_id):
        db = SessionLocal()
        transfer = db.query(Transfer).filter_by(id=transfer_id).first()
        if transfer:
            db.delete(transfer)
            db.commit()
        db.close()

    def editTransfer(self, transfer_type, transfer_id, data):
        data = dict(data)
        transfer_type = transfer_type == "1"
        clinic_name = data.get("clinic_name")
        date_obj = data.get("date")

        db = SessionLocal()
        transfer = db.query(Transfer).filter_by(id=transfer_id).first()
        if not transfer:
            db.close()
            return None
        
        # Update fields
        transfer.transfer_type = transfer_type
        transfer.clinic_name = clinic_name
        transfer.date = datetime.strptime(date_obj, "%Y-%m-%d").date()

        db.commit()
        db.refresh(transfer)
        db.close()

    def get_meetings(self, meeting_type="general"):
        db = SessionLocal()
        try:
            q = (
                db.query(Meeting)
                .options(joinedload(Meeting.patient))
                .join(Patient, Meeting.patient_id == Patient.id)
                .filter(Meeting.meeting_type == meeting_type)
            )
            q = _apply_doctor_filter(q)
            rows = q.order_by(desc(Meeting.date), desc(Meeting.time), desc(Meeting.id)).all()
            return [
                {
                    "id": m.id,
                    "meeting_type": m.meeting_type,
                    "meeting_type_2": m.meeting_type_2,
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
                    },
                }
                for m in rows
            ]
        finally:
            db.close()

    def load_patient(self):
        db = SessionLocal()
        try:
            p = db.query(Patient).filter_by(id=current_patient_id).first()
            if not p:
                return None

            print(f"Loaded patient: {p.name} , id: {p.id}")

            # sort the related collections before serializing
            sorted_meetings = _sort_meetings(p.meetings)
            sorted_transfers = _sort_transfers(p.transfers)
            sorted_payments = _sort_payments(p.payments)

            return {
                "id": p.id,
                "page_to_load": page_to_load,
                "name": p.name,
                "doctor": p.doctor,
                "phone_num": p.phone_num,
                "creation_date": p.creation_date.isoformat() if p.creation_date else None,
                "treat_type": p.treat_type,
                "transfer_state": p.transfer_state,
                "meetings": [
                    {
                        "id": m.id,
                        "meeting_type": m.meeting_type,
                        "meeting_type_2": m.meeting_type_2,
                        "info": m.info,
                        "date": m.date.isoformat() if m.date else None,
                        "time": m.time,
                    }
                    for m in sorted_meetings
                ],
                "transfers": [
                    {
                        "id": t.id,
                        "transfer_type": t.transfer_type,
                        "date": t.date.isoformat() if t.date else None,
                        "clinic_name": t.clinic_name,
                    }
                    for t in sorted_transfers
                ],
                "payments": [
                    {
                        "id": p.id,
                        "amount": p.amount,
                        "date": p.date.isoformat() if p.date else None,
                    }
                    for p in sorted_payments
                ],
            }
        finally:
            db.close()

    def set_current_patient(self, pid, page):
        global current_patient_id, page_to_load
        current_patient_id = pid
        page_to_load = page
        print(f"Set current patient to ID: {current_patient_id}, page_to_load: {page_to_load}")


    def setTreatmentType(self, treat_type, pid):
        db = SessionLocal()
        try:
            p = db.query(Patient).filter_by(id=pid).first()
            if not p:
                return None

            p.treat_type = treat_type
            db.commit()
            db.refresh(p)
            return p.treat_type
        finally:
            db.close()

    def changeCurrentDoctor(self, doctor):
        global current_doctor
        current_doctor = doctor
        print(f"Changed current doctor to: {current_doctor}")
        return current_doctor
    
    def getCurrentDoctor(self):
        global current_doctor
        print(f"Current doctor is: {current_doctor}")
        return current_doctor


def on_loaded():
    # This will maximize the window after creation
    webview.windows[0].maximize()

# --- Start app ---
api = API()
window = webview.create_window("Dentister", load_page("index"), js_api=api, resizable=False)
webview.start(on_loaded)
