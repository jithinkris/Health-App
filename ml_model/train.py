import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib
import os

# Set random seed for reproducibility
np.random.seed(42)

# Generate synthetic dataset of 5,000 samples with 22 features
n_samples = 5000

# Feature definitions
age = np.random.randint(18, 85, n_samples)
gender = np.random.choice([0.0, 1.0], n_samples, p=[0.5, 0.5])  # 0: Female, 1: Male
bmi = np.random.uniform(17.0, 42.0, n_samples)
heart_rate = np.random.randint(55, 115, n_samples)
sleep_hours = np.random.uniform(4.0, 9.5, n_samples)
steps = np.random.randint(1000, 18000, n_samples)
spo2 = np.random.uniform(88.0, 100.0, n_samples)
calories = steps * 0.05 + np.random.randint(1200, 2200, n_samples)
stress_level = np.random.uniform(10.0, 95.0, n_samples)
hrv = 100 - (age * 0.4) - (stress_level * 0.3) + np.random.normal(0, 8, n_samples)
hrv = np.clip(hrv, 15, 120)

snoring_events = np.random.poisson(lam=2, size=n_samples)
# Elevate snoring for high BMI individuals
snoring_events = np.where(bmi > 28, snoring_events + np.random.randint(2, 8, n_samples), snoring_events)

spo2_drops = np.random.poisson(lam=0.5, size=n_samples)
spo2_drops = np.where(snoring_events > 5, spo2_drops + np.random.randint(1, 4, n_samples), spo2_drops)

irregular_hr_events = np.random.choice([0, 1, 2], n_samples, p=[0.85, 0.10, 0.05])
irregular_hr_events = np.where(age > 65, irregular_hr_events + np.random.choice([0, 1], n_samples, p=[0.6, 0.4]), irregular_hr_events)

sitting_time = np.random.uniform(2.0, 12.0, n_samples)

# Lab reports (BP, glucose, cholesterol etc.)
bp_systolic = 105 + (age * 0.25) + (bmi * 0.3) + np.random.normal(0, 10, n_samples)
bp_diastolic = 65 + (age * 0.1) + (bmi * 0.2) + np.random.normal(0, 6, n_samples)
glucose = 75 + (bmi * 0.6) + (age * 0.15) + np.random.normal(0, 12, n_samples)
hemoglobin = np.random.normal(14.0, 1.5, n_samples)
cholesterol_total = 140 + (age * 0.6) + (bmi * 0.8) + np.random.normal(0, 15, n_samples)
hdl = 65 - (bmi * 0.4) + np.random.normal(0, 5, n_samples)
ldl = cholesterol_total - hdl - np.random.uniform(15, 35, n_samples)
triglycerides = 90 + (bmi * 1.8) + np.random.normal(0, 25, n_samples)

# Assemble DataFrame
features_df = pd.DataFrame({
    'Age': age,
    'Gender': gender,
    'BMI': bmi,
    'Heart_Rate': heart_rate,
    'Sleep_Hours': sleep_hours,
    'Steps': steps,
    'SpO2': spo2,
    'Calories': calories,
    'Stress_Level': stress_level,
    'HRV': hrv,
    'Snoring_Events': snoring_events,
    'SpO2_Drops': spo2_drops,
    'Irregular_HR_Events': irregular_hr_events,
    'Sitting_Time': sitting_time,
    'Blood_Pressure_Systolic': bp_systolic,
    'Blood_Pressure_Diastolic': bp_diastolic,
    'Glucose': glucose,
    'Hemoglobin': hemoglobin,
    'Cholesterol_Total': cholesterol_total,
    'HDL': hdl,
    'LDL': ldl,
    'Triglycerides': triglycerides
})

# Define targets and rule-based clinical correlations
def label_general_risk(row):
    score = 0
    if row['Age'] > 55: score += 1
    if row['BMI'] > 30: score += 1
    if row['Heart_Rate'] > 100 or row['Heart_Rate'] < 60: score += 1
    if row['Sleep_Hours'] < 5.5: score += 1
    if row['Steps'] < 4000: score += 1
    if row['SpO2'] < 93: score += 2
    if row['Stress_Level'] > 65: score += 1
    if row['Irregular_HR_Events'] > 0: score += 1
    if row['Blood_Pressure_Systolic'] > 140: score += 1.5
    if row['Glucose'] > 126: score += 1.5
    if row['Cholesterol_Total'] > 240: score += 1
    return 'HIGH' if score >= 5.0 else ('MEDIUM' if score >= 2.5 else 'LOW')

def label_hypertension(row):
    if row['Blood_Pressure_Systolic'] > 140 or row['Blood_Pressure_Diastolic'] > 90:
        return 'HIGH'
    if row['Blood_Pressure_Systolic'] > 125 or row['Blood_Pressure_Diastolic'] > 80:
        return 'MEDIUM'
    return 'LOW'

def label_cardiovascular(row):
    score = 0
    if row['Blood_Pressure_Systolic'] > 135: score += 2
    if row['Cholesterol_Total'] > 220: score += 1.5
    if row['LDL'] > 130: score += 1.5
    if row['HDL'] < 40: score += 1
    if row['Irregular_HR_Events'] > 0: score += 3
    if row['HRV'] < 30: score += 1
    if row['Heart_Rate'] > 95: score += 1
    return 'HIGH' if score >= 4.0 else ('MEDIUM' if score >= 2.0 else 'LOW')

def label_sleep_apnea(row):
    if row['Snoring_Events'] >= 8 and row['SpO2_Drops'] >= 3 and row['BMI'] >= 28:
        return 'HIGH'
    if row['Snoring_Events'] >= 4 and row['SpO2_Drops'] >= 1:
        return 'MEDIUM'
    return 'LOW'

def label_stress(row):
    if row['Stress_Level'] > 65 and row['HRV'] < 30:
        return 'HIGH'
    if row['Stress_Level'] > 45 or row['HRV'] < 45:
        return 'MEDIUM'
    return 'LOW'

def label_arrhythmia(row):
    if row['Irregular_HR_Events'] >= 2 or (row['Irregular_HR_Events'] >= 1 and row['HRV'] < 30):
        return 'HIGH'
    if row['Irregular_HR_Events'] == 1 or row['HRV'] < 35:
        return 'MEDIUM'
    return 'LOW'

def label_obesity(row):
    if row['BMI'] >= 30: return 'HIGH'
    if row['BMI'] >= 25: return 'MEDIUM'
    return 'LOW'

def label_diabetes(row):
    if row['Glucose'] >= 126: return 'HIGH'
    if row['Glucose'] >= 100: return 'MEDIUM'
    return 'LOW'

def label_fatigue(row):
    if row['Sleep_Hours'] < 5.0 and row['Stress_Level'] > 55: return 'HIGH'
    if row['Sleep_Hours'] < 6.2 or row['Stress_Level'] > 40: return 'MEDIUM'
    return 'LOW'

def label_depression(row):
    if row['Stress_Level'] > 70 and row['Sleep_Hours'] < 5.5 and row['Steps'] < 3500:
        return 'HIGH'
    if row['Stress_Level'] > 50 or row['Sleep_Hours'] < 6.0:
        return 'MEDIUM'
    return 'LOW'

def label_fall_elderly(row):
    if row['Age'] >= 65 and row['Steps'] < 3000: return 'HIGH'
    if row['Age'] >= 60 and row['Steps'] < 4500: return 'MEDIUM'
    return 'LOW'

def label_sedentary(row):
    if row['Sitting_Time'] > 8.5 and row['Steps'] < 3500: return 'HIGH'
    if row['Sitting_Time'] > 7.0 or row['Steps'] < 5000: return 'MEDIUM'
    return 'LOW'

# Define models list: (label_function, save_filename)
models_to_train = [
    (label_general_risk, 'risk_model.pkl'),
    (label_hypertension, 'hypertension_rf.pkl'),
    (label_cardiovascular, 'cardiovascular_xgb.pkl'),  # Kept original names
    (label_sleep_apnea, 'sleep_apnea_cnn.h5'),
    (label_stress, 'stress_svm.pkl'),
    (label_arrhythmia, 'arrhythmia_dl.h5'),
    (label_obesity, 'obesity_lr.pkl'),
    (label_diabetes, 'diabetes_xgb.pkl'),
    (label_fatigue, 'fatigue_rf.pkl'),
    (label_depression, 'depression_lstm.h5'),
    (label_fall_elderly, 'fall_cnn.h5'),
    (label_sedentary, 'sedentary_dt.pkl')
]

output_dir = os.path.dirname(os.path.abspath(__file__))

print("Starting training of 12 RandomForestClassifier models...")

for label_fn, filename in models_to_train:
    labels = features_df.apply(label_fn, axis=1)
    
    # Train test split
    X_train, X_test, y_train, y_test = train_test_split(features_df, labels, test_size=0.2, random_state=42)
    
    # RandomForestClassifier is a great general clinical risk estimator
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X_train, y_train)
    
    # Evaluate
    preds = clf.predict(X_test)
    acc = accuracy_score(y_test, preds)
    print(f"Model: {filename:<25} | Accuracy: {acc*100:.2f}% | Class Dist: {dict(labels.value_counts())}")
    
    # Save model
    model_path = os.path.join(output_dir, filename)
    joblib.dump(clf, model_path)

print("\nAll 12 ML models trained and saved successfully!")
