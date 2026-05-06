import random
import os

os.makedirs('tests', exist_ok=True)
with open('tests/synthetic_data.py', 'w', encoding='utf-8') as f:
    f.write('"""\n')
    f.write('Synthetic Patient Dataset for Machine Learning and System Testing.\n')
    f.write('This module provides a large dataset of synthetic medical records\n')
    f.write('to validate the stroke prediction logic, stress-test the database,\n')
    f.write('and ensure the system handles edge cases correctly.\n')
    f.write('"""\n\n')
    f.write('SYNTHETIC_PATIENTS = [\n')
    
    for i in range(3500):
        age = round(random.uniform(20.0, 90.0), 1)
        gender = random.choice(['Male', 'Female'])
        hypertension = random.choice([0, 1])
        heart_disease = random.choice([0, 1])
        bmi = round(random.uniform(15.0, 45.0), 1)
        glucose = round(random.uniform(60.0, 250.0), 1)
        smoke = random.choice(['never smoked', 'formerly smoked', 'smokes', 'Unknown'])
        work = random.choice(['Private', 'Self-employed', 'Govt_job', 'children', 'Never_worked'])
        married = random.choice(['Yes', 'No'])
        residence = random.choice(['Urban', 'Rural'])
        fast_f = random.choice([0, 1, 2, 3])
        fast_a = random.choice([0, 1, 2, 3])
        fast_s = random.choice([0, 1, 2, 3])
        fast_t = random.choice([0, 1, 2, 3])
        
        record = f"    {{'id': {i+1}, 'age': {age}, 'gender': '{gender}', 'hypertension': {hypertension}, 'heart_disease': {heart_disease}, 'ever_married': '{married}', 'work_type': '{work}', 'Residence_type': '{residence}', 'avg_glucose_level': {glucose}, 'bmi': {bmi}, 'smoking_status': '{smoke}', 'fast_f': {fast_f}, 'fast_a': {fast_a}, 'fast_s': {fast_s}, 'fast_t': {fast_t}}},\n"
        f.write(record)
        
    f.write(']\n\n')
    f.write('def get_high_risk_patients():\n')
    f.write('    return [p for p in SYNTHETIC_PATIENTS if p["age"] > 60 and (p["hypertension"] == 1 or p["heart_disease"] == 1)]\n\n')
    f.write('def get_ml_test_batch(size=100):\n')
    f.write('    import random\n')
    f.write('    return random.sample(SYNTHETIC_PATIENTS, min(size, len(SYNTHETIC_PATIENTS)))\n')
