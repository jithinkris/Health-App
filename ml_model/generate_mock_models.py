import os
import joblib

class MockModel:
    def predict(self, X):
        import random
        return [random.choice(['LOW', 'MEDIUM', 'HIGH'])]
        
    def predict_proba(self, X):
        import random
        return [[random.random(), random.random(), random.random()]]

def generate_mock_models():
    models = [
        'hypertension_rf.pkl',
        'cardiovascular_xgb.pkl',
        'stress_svm.pkl',
        'obesity_lr.pkl',
        'diabetes_xgb.pkl',
        'fatigue_rf.pkl',
        'sedentary_dt.pkl'
    ]
    
    output_dir = os.path.dirname(os.path.abspath(__file__))
    
    for m in models:
        path = os.path.join(output_dir, m)
        print(f"Generating mock model: {path}")
        joblib.dump(MockModel(), path)
        
    # for .h5 models (deep learning) we just create empty files for now as a placeholder
    h5_models = [
        'sleep_apnea_cnn.h5',
        'arrhythmia_dl.h5',
        'depression_lstm.h5',
        'fall_cnn.h5'
    ]
    
    for h in h5_models:
        path = os.path.join(output_dir, h)
        print(f"Creating empty placeholder for DL model: {path}")
        with open(path, 'w') as f:
            f.write("Placeholder for Keras/TensorFlow model")
            
if __name__ == '__main__':
    generate_mock_models()
