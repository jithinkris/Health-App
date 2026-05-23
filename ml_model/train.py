import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import joblib
import os

# Set random seed for reproducibility
np.random.seed(42)

# Generate synthetic data
n_samples = 2000

# Features: Age, BMI, Heart Rate, Sleep Duration, Activity Level, Steps Count, SpO2
data = {
    'Age': np.random.randint(18, 80, n_samples),
    'BMI': np.random.uniform(18.5, 40.0, n_samples),
    'Heart_Rate': np.random.randint(50, 120, n_samples),
    'Sleep_Duration': np.random.uniform(3.0, 10.0, n_samples),
    'Activity_Level': np.random.randint(0, 3, n_samples), # 0: Low, 1: Medium, 2: High
    'Steps_Count': np.random.randint(1000, 20000, n_samples),
    'SpO2': np.random.uniform(85.0, 100.0, n_samples),
}

df = pd.DataFrame(data)

# Risk logic (heuristic for synthetic generation)
def calculate_risk(row):
    score = 0
    if row['Age'] > 55: score += 2
    elif row['Age'] > 40: score += 1
    
    if row['BMI'] > 30: score += 2
    elif row['BMI'] > 25: score += 1
    
    if row['Heart_Rate'] > 100 or row['Heart_Rate'] < 60: score += 2
    
    if row['Sleep_Duration'] < 5: score += 2
    elif row['Sleep_Duration'] < 7: score += 1
    
    if row['Activity_Level'] == 0: score += 2
    elif row['Activity_Level'] == 1: score += 1
    
    if row['Steps_Count'] < 3000: score += 2
    elif row['Steps_Count'] < 7000: score += 1
    
    if row['SpO2'] < 90: score += 3
    elif row['SpO2'] < 95: score += 1
    
    if score >= 8: return 'HIGH'
    elif score >= 4: return 'MEDIUM'
    else: return 'LOW'

df['Risk_Level'] = df.apply(calculate_risk, axis=1)

print("Distribution of Synthetic Data Risk Levels:")
print(df['Risk_Level'].value_counts())

X = df.drop('Risk_Level', axis=1)
y = df['Risk_Level']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(X_train, y_train)

y_pred = clf.predict(X_test)
print(f"\nAccuracy: {accuracy_score(y_test, y_pred):.2f}")
print("Classification Report:")
print(classification_report(y_test, y_pred))

# Save the model
model_path = os.path.join(os.path.dirname(__file__), 'risk_model.pkl')
joblib.dump(clf, model_path)
print(f"\nModel saved successfully to {model_path}")
