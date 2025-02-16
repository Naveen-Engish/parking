from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define parking rates (per hour)
RATES = {
    'Car': 2.0,
    'Motorcycle': 1.0,
    'Truck': 3.0
}

# Define parking slots (A1-A20, B1-B20, ..., F1-F20)
SLOTS = [f"{row}{col}" for row in "ABCDEF" for col in range(1, 21)]

class ParkingRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_number = db.Column(db.String(20), nullable=False)
    vehicle_class = db.Column(db.String(20), nullable=False)
    entry_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    exit_time = db.Column(db.DateTime)
    cost = db.Column(db.Float)
    slot = db.Column(db.String(10), nullable=False)

    def __repr__(self):
        return f'<Vehicle {self.vehicle_number} ({self.vehicle_class}) in {self.slot}>'

with app.app_context():
    db.create_all()

def get_available_slot():
    """Find the first available slot."""
    occupied_slots = {record.slot for record in ParkingRecord.query.filter_by(exit_time=None).all()}
    for slot in SLOTS:
        if slot not in occupied_slots:
            return slot
    return None

@app.route('/')
def index():
    occupied_slots = ParkingRecord.query.filter_by(exit_time=None).count()
    total_slots = len(SLOTS)
    occupied_records = ParkingRecord.query.filter_by(exit_time=None).all()
    slot_status = {slot: ParkingRecord.query.filter_by(slot=slot, exit_time=None).first() for slot in SLOTS}
    
    return render_template(
        'index.html',
        occupied_slots=occupied_slots,
        total_slots=total_slots,
        SLOTS=SLOTS,
        slot_status=slot_status,  # Pass slot status (occupied/free) to the template
        occupied_records=occupied_records  # Pass occupied records to the template
    )


@app.route('/entry', methods=['GET', 'POST'])
def entry():
    if request.method == 'POST':
        vehicle_number = request.form['vehicle_number'].upper()
        vehicle_class = request.form['vehicle_class']
        
        slot = get_available_slot()
        if not slot:
            return "No available slots!"

        new_entry = ParkingRecord(
            vehicle_number=vehicle_number,
            vehicle_class=vehicle_class,
            slot=slot
        )
        db.session.add(new_entry)
        db.session.commit()
        
        return render_template('entry.html', slot=slot, vehicle_number=vehicle_number)
    return render_template('entry.html')

@app.route('/exit', methods=['GET', 'POST'])
def exit_vehicle():
    if request.method == 'POST':
        vehicle_number = request.form['vehicle_number'].upper()
        record = ParkingRecord.query.filter_by(
            vehicle_number=vehicle_number,
            exit_time=None
        ).first()

        if record:
            record.exit_time = datetime.utcnow()
            duration = record.exit_time - record.entry_time
            hours = duration.total_seconds() / 3600
            rate = RATES.get(record.vehicle_class, 1.0)
            record.cost = round(hours * rate, 2)
            db.session.commit()
            return render_template('exit.html', cost=record.cost, vehicle=vehicle_number, slot=record.slot)
        return "Vehicle not found or already exited!"
    return render_template('exit.html')

@app.route('/history')
def history():
    records = ParkingRecord.query.all()
    return render_template('history.html', records=records)

if __name__ == '__main__':
    app.run(debug=True)