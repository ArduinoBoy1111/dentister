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


def _rand_phone(existing: set) -> str:
    """
    Iraqi mobile numbers are 11 digits, starting with '07'.
    Ensures uniqueness within this seeding session.
    """
    while True:
        num = "07" + "".join(str(random.randint(0, 9)) for _ in range(9))
        if num not in existing:
            existing.add(num)
            return num

def _weighted_choice(items_with_weights):
    items, weights = zip(*items_with_weights)
    return random.choices(items, weights=weights, k=1)[0]

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
                ["adb", "shell", "am", "start", "-a", "android.intent.action.CALL", "-d", f"tel:{num}"],
                startupinfo=startupinfo
            )

    # --- Patients ---
    def createPatient(self, data):
        data = dict(data)
        name = data.get("name")
        phone_num = data.get("phone_num")
        doctor = data.get("doctor")
        implant_total = data.get("implant_total", 0)

        db = SessionLocal()
        patient = Patient(
            name=name,
            phone_num=phone_num,
            doctor=doctor,
            creation_date=date.today(),
            implant_total=implant_total
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
                    "implant_total": p.implant_total or 0,
                    "implant_current": p.implant_current or 0,
                    "implant_state": p.implant_state,
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

    def get_patient(self, pid):
        db = SessionLocal()
        patient = db.query(Patient).filter(Patient.id == pid).first()
        db.close()
        if not patient:
            return None
        return {
            "id": patient.id,
            "name": patient.name,
            "phone_num": patient.phone_num,
            "doctor": patient.doctor,
            "creation_date": patient.creation_date.isoformat()
        }

    def editPatient(self, data, pid):
        data = dict(data)
        name = data.get("name")
        phone_num = data.get("phone_num")
        implant_total = data.get("implant_total")
        implant_current = data.get("implant_current")
        treat_type = data.get("treat_type")

        db = SessionLocal()
        patient = db.query(Patient).filter(Patient.id == pid).first()
        if not patient:
            db.close()
            return None

        patient.name = name
        patient.phone_num = phone_num
        if treat_type and treat_type != "":
            patient.treat_type = treat_type

        if implant_total and implant_total != "":
            patient.implant_total = implant_total

        if implant_current and implant_current != "":
            patient.implant_current = implant_current

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
        info = data.get("info")
        date_obj = data.get("date")
        meeting_type = meeting_type

        db = SessionLocal()
        new_meeting = Meeting(
            info=info,
            date=datetime.strptime(date_obj, "%Y-%m-%d").date(),
            time=time,
            meeting_type=meeting_type
        )

        patient = db.query(Patient).filter_by(id=id).first()
        patient.meetings.append(new_meeting)

        if id:
            patient = db.query(Patient).filter_by(id=id).first()
            patient.meetings.append(new_meeting)
            if patient.implant_total == 0:
                implant_total = data.get("implant_total")
                if implant_total and float(implant_total) > 0:
                    patient.implant_total = implant_total

        db.commit()
        db.refresh(new_meeting)
        db.close()

    def editMeeting(self, meeting_id, data, time, patient_id):
        data = dict(data)
        info = data.get("info")
        date_str = data.get("date")
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()

        db = SessionLocal()
        meeting = db.query(Meeting).filter_by(id=meeting_id).first()
        if not meeting:
            db.close()
            return None

        # Update fields
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

            return {
                "id": p.id,
                "page_to_load": page_to_load,
                "name": p.name,
                "doctor": p.doctor,
                "phone_num": p.phone_num,
                "creation_date": p.creation_date.isoformat() if p.creation_date else None,
                "treat_type": p.treat_type,
                "transfer_state": p.transfer_state,
                "implant_total": p.implant_total or 0,
                "implant_current": p.implant_current or 0,
                "implant_state": p.implant_state,
                "meetings": [
                    {
                        "id": m.id,
                        "meeting_type": m.meeting_type,
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
            }
        finally:
            db.close()

    def set_current_patient(self, pid, page):
        global current_patient_id, page_to_load
        current_patient_id = pid
        page_to_load = page
        print(f"Set current patient to ID: {current_patient_id}, page_to_load: {page_to_load}")

    def setImplantAmount(self, amount, pid):
        db = SessionLocal()
        try:
            p = db.query(Patient).filter_by(id=pid).first()
            if not p:
                return None

            p.implant_total = amount
            db.commit()
            db.refresh(p)
            return p.implant_total
        finally:
            db.close()

    def addAmount(self, amount, pid):
        # get the iimplant_current and adds the amount on it then refresh the patient
        db = SessionLocal()
        try:
            p = db.query(Patient).filter_by(id=pid).first()
            if not p:
                return None

            p.implant_current += float(amount)
            db.commit()
            db.refresh(p)
            return p.implant_current
        finally:
            db.close()

    def resetAmounts(self, pid):
        db = SessionLocal()
        try:
            p = db.query(Patient).filter_by(id=pid).first()
            if not p:
                return None

            p.implant_current = 0
            p.implant_total = 0
            p.implant_state = False
            db.commit()
            db.refresh(p)
            return p.implant_current
        finally:
            db.close()

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

    def doneifyPatient(self, pid):
        db = SessionLocal()
        try:
            p = db.query(Patient).filter_by(id=pid).first()
            if not p:
                return None

            p.implant_state = True
            db.commit()
            db.refresh(p)
            return p.implant_state
        finally:
            db.close()

    def resetTreatment(self, pid):
        db = SessionLocal()
        try:
            p = db.query(Patient).filter_by(id=pid).first()
            if not p:
                return None

            p.treat_type = "none"
            p.implant_state = False
            db.commit()
            db.refresh(p)
            return p.treat_type
        finally:
            db.close()
            
    def seed_demo(self, count: int = 50, seed: int | None = 42, clear: bool = False):
        """
        Generate demo data: `count` Patients with random Meetings and Transfers.
        - Realistic Arabic names, clinics, notes.
        - Dates spread across recent months/next weeks.
        - Phone numbers Iraqi-style, unique within this run.
        - Keeps your sorting logic working (dates are real Date objects).
        
        Call from JS: window.pywebview.api.seed_demo(50, 42, false)
        """
        if seed is not None:
            random.seed(seed)

        db = SessionLocal()
        try:
            if clear:
                db.query(Meeting).delete()
                db.query(Transfer).delete()
                db.query(Patient).delete()
                db.commit()

            first_names = [
                "حسن","حسين","علي","محمد","مهند","مصطفى","يوسف","كرار","مرتضى","أحمد",
                "نور","فاطمة","زهراء","مريم","سارة","بتول","رقيّة","هدى","آمنة","زينب"
            ]
            second_name = [
                "حسن","حسين","علي","محمد","مهند","مصطفى","يوسف","كرار","مرتضى","أحمد",
                "نور","فاطمة","زهراء","مريم","سارة","بتول","رقيّة","هدى","آمنة","زينب"
            ]
            last_names = [
                "التميمي","الهاشمي","العطواني","الكعبي","الموسوي","الشمري","الجنابي",
                "الدليمي","الطائي","السعدي","البياتي","الربيعي","الزيدي","الجبوري"
            ]
            doctors = ["0","0","1", "1","2", "2"]  # Seen in your data ,"01","02","12","012"

            # Seen in your data + common ones
            treat_types = ["none", "زراعة", "متحرك", "تغليف", "ابتسامة"]
            clinics = ["العيادة","الجوهرة","التراث","الأحلام","الالماس","العميد","الواقعة","الشفاء","المستقبل","الواحة"]

            meeting_types = ["general", "implant", "braces"]
            general_infos = ["حشوة","حشوة جذر","تنظيف","تبييض","قلع","قلع سن العقل","تصليح كسر","علاج لثة"]
            implant_infos = ["زراعة","زراعة كاملة","تثبيت مسمار","تركيب دعامة","كشف لثة"]
            braces_infos  = ["تقويم علوي","تقويم سفلي","تقويم علوي حديدي","تقويم سفلي حديدي","شد أسلاك","استبدال مطاط"]

            # weights to make data look natural
            treat_weights = {
                "none": 40, "زراعة": 25, "متحرك": 15, "تغليف": 10, "ابتسامة": 10
            }
            meeting_type_weights = {
                "general": 60, "implant": 25, "braces": 15
            }

            used_phones = set()
            created_patients = 0
            created_meetings = 0
            created_transfers = 0

            today = date.today()

            for _ in range(count):
                # --- Patient core ---
                name = f"{random.choice(first_names)} {random.choice(second_name)} {random.choice(last_names)}"
                phone = _rand_phone(used_phones)
                doctor = random.choice(doctors)

                # Creation date within last ~180 days
                creation_date = today - timedelta(days=random.randint(0, 180))

                treat_type = _weighted_choice([(k, v) for k, v in treat_weights.items()])
                implant_total = 0
                implant_current = 0
                implant_state = False

                if treat_type in ("زراعة", "تغليف", "ابتسامة"):
                    # set some realistic totals
                    implant_total = random.choice([600_000, 800_000, 1_000_000, 1_300_000, 1_500_000])
                    implant_current = random.choice([0, implant_total // 10, implant_total // 5, implant_total // 2])
                    implant_state = random.choice([False, False, True])  # mostly not done yet

                p = Patient(
                    name=name,
                    phone_num=phone,
                    doctor=doctor,
                    creation_date=creation_date,
                    treat_type=treat_type,
                    transfer_state=False,
                    implant_total=implant_total,
                    implant_current=implant_current,
                    implant_state=implant_state
                )
                db.add(p)
                db.flush()  # get p.id without full commit
                created_patients += 1

                # --- Transfers (0–5 each) ---
                n_transfers = random.choices([0, 1, 2, 3], weights=[55, 25, 15, 5], k=1)[0]
                for _t in range(n_transfers):
                    t_date = creation_date + timedelta(days=random.randint(0, 150))
                    t = Transfer(
                        transfer_type=random.choice([True, False]),
                        date=t_date,
                        clinic_name=random.choice(clinics),
                        patient_id=p.id
                    )
                    db.add(t)
                    created_transfers += 1

                # --- Meetings (1–5 each) ---
                n_meetings = random.choices([1, 2, 3, 4, 5], weights=[30, 30, 20, 15, 5], k=1)[0]
                for _m in range(n_meetings):
                    mtype = _weighted_choice([(k, v) for k, v in meeting_type_weights.items()])
                    # dates around recent 90 days +/- a little into future
                    m_date = today + timedelta(days=random.randint(-120, 120))
                    m_time = random.choice([0, 1])  # 0: evening, 1: morning

                    if mtype == "general":
                        info = random.choice(general_infos)
                    elif mtype == "implant":
                        info = random.choice(implant_infos)
                    else:
                        info = random.choice(braces_infos)

                    m = Meeting(
                        meeting_type=mtype,
                        info=info,
                        date=m_date,
                        time=m_time,
                        patient_id=p.id
                    )
                    db.add(m)
                    created_meetings += 1

            db.commit()
            return {
                "patients": created_patients,
                "meetings": created_meetings,
                "transfers": created_transfers
            }
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
api.seed_demo(2000, seed=random.randint(0, 1005678), clear=True)
window = webview.create_window("Dentister", load_page("index"), js_api=api, resizable=False)
webview.start(on_loaded)
