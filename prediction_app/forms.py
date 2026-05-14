from django import forms
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext_lazy as _
from .models import DiseaseModel, Prediction, Symptom, PatientSymptom


class DiseaseModelForm(forms.ModelForm):
    """Form for DiseaseModel."""
    
    class Meta:
        model = DiseaseModel
        fields = '__all__'
        widgets = {
            'model_file': forms.FileInput(attrs={
                'accept': '.pkl,.joblib',
                'class': 'form-control'
            }),
            'scaler_file': forms.FileInput(attrs={
                'accept': '.pkl,.joblib',
                'class': 'form-control'
            }),
        }
    
    def clean_model_file(self):
        """Validate model file."""
        model_file = self.cleaned_data.get('model_file')
        if model_file:
            # Check file extension
            if not model_file.name.endswith(('.pkl', '.joblib')):
                raise forms.ValidationError(
                    'Only .pkl or .joblib files are allowed for models.'
                )
            
            # Check file size (max 100MB)
            if model_file.size > 100 * 1024 * 1024:
                raise forms.ValidationError(
                    'Model file size must be less than 100MB.'
                )
        
        return model_file
    
    def clean_accuracy(self):
        """Validate accuracy value."""
        accuracy = self.cleaned_data.get('accuracy')
        if accuracy is not None:
            if accuracy < 0 or accuracy > 1:
                raise forms.ValidationError(
                    'Accuracy must be between 0 and 1.'
                )
        return accuracy


class PredictionForm(forms.ModelForm):
    """Form for Prediction (admin use only)."""
    
    class Meta:
        model = Prediction
        fields = ['user', 'disease_model', 'prediction_result', 
                 'prediction_label', 'confidence', 'input_data']
        widgets = {
            'input_data': forms.Textarea(attrs={
                'rows': 10,
                'class': 'form-control',
                'placeholder': 'Enter JSON data'
            }),
        }
    
    def clean_input_data(self):
        """Validate input data JSON."""
        import json
        input_data = self.cleaned_data.get('input_data')
        
        try:
            if isinstance(input_data, str):
                json.loads(input_data)
            elif not isinstance(input_data, dict):
                raise forms.ValidationError('Input data must be valid JSON.')
        except json.JSONDecodeError:
            raise forms.ValidationError('Invalid JSON format.')
        
        return input_data


class SymptomForm(forms.ModelForm):
    """Form for Symptom."""
    
    class Meta:
        model = Symptom
        fields = '__all__'
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'severity_levels': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Enter JSON object with severity levels'
            }),
        }
    
    def clean_severity_levels(self):
        """Validate severity levels JSON."""
        import json
        severity_levels = self.cleaned_data.get('severity_levels')
        
        try:
            if severity_levels:
                if isinstance(severity_levels, str):
                    data = json.loads(severity_levels)
                else:
                    data = severity_levels
                
                if not isinstance(data, dict):
                    raise forms.ValidationError('Severity levels must be a JSON object.')
        except json.JSONDecodeError:
            raise forms.ValidationError('Invalid JSON format for severity levels.')
        
        return severity_levels


class PatientSymptomForm(forms.ModelForm):
    """Form for PatientSymptom."""
    
    class Meta:
        model = PatientSymptom
        fields = ['symptom', 'severity', 'onset_date', 'duration_days', 'notes']
        widgets = {
            'onset_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean_severity(self):
        """Validate severity value."""
        severity = self.cleaned_data.get('severity')
        if severity < 1 or severity > 10:
            raise forms.ValidationError('Severity must be between 1 and 10.')
        return severity
    
    def clean_duration_days(self):
        """Validate duration days."""
        duration = self.cleaned_data.get('duration_days')
        if duration < 1:
            raise forms.ValidationError('Duration must be at least 1 day.')
        return duration


# Disease-specific prediction forms
class DiabetesPredictionForm(forms.Form):
    """Form for diabetes prediction."""
    
    pregnancies = forms.IntegerField(
        min_value=0, max_value=20,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Number of times pregnant'
        })
    )
    glucose = forms.FloatField(
        min_value=0, max_value=300,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.1',
            'placeholder': 'Glucose concentration (mg/dL)'
        })
    )
    blood_pressure = forms.FloatField(
        min_value=0, max_value=200,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.1',
            'placeholder': 'Diastolic blood pressure (mm Hg)'
        })
    )
    skin_thickness = forms.FloatField(
        min_value=0, max_value=100,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.1',
            'placeholder': 'Triceps skin fold thickness (mm)'
        })
    )
    insulin = forms.FloatField(
        min_value=0, max_value=900,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.1',
            'placeholder': '2-Hour serum insulin (mu U/ml)'
        })
    )
    bmi = forms.FloatField(
        min_value=0, max_value=100,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.1',
            'placeholder': 'Body mass index (kg/m²)'
        })
    )
    diabetes_pedigree_function = forms.FloatField(
        min_value=0, max_value=3,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.001',
            'placeholder': 'Diabetes pedigree function'
        })
    )
    age = forms.IntegerField(
        min_value=0, max_value=120,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Age (years)'
        })
    )


class HeartDiseasePredictionForm(forms.Form):
    """Form for heart disease prediction."""
    
    age = forms.IntegerField(
        min_value=0, max_value=120,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    sex = forms.ChoiceField(
        choices=[(0, 'Female'), (1, 'Male')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    cp = forms.ChoiceField(
        choices=[
            (0, 'Typical Angina'),
            (1, 'Atypical Angina'),
            (2, 'Non-anginal Pain'),
            (3, 'Asymptomatic')
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    trestbps = forms.IntegerField(
        label='Resting Blood Pressure',
        min_value=0, max_value=300,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    chol = forms.IntegerField(
        label='Cholesterol',
        min_value=0, max_value=600,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    fbs = forms.ChoiceField(
        label='Fasting Blood Sugar > 120 mg/dL',
        choices=[(0, 'False'), (1, 'True')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    restecg = forms.ChoiceField(
        label='Resting Electrocardiographic Results',
        choices=[
            (0, 'Normal'),
            (1, 'ST-T Wave Abnormality'),
            (2, 'Left Ventricular Hypertrophy')
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    thalach = forms.IntegerField(
        label='Maximum Heart Rate Achieved',
        min_value=0, max_value=300,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    exang = forms.ChoiceField(
        label='Exercise Induced Angina',
        choices=[(0, 'No'), (1, 'Yes')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    oldpeak = forms.FloatField(
        label='ST Depression Induced by Exercise',
        min_value=0, max_value=10,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'})
    )
    slope = forms.ChoiceField(
        choices=[
            (0, 'Upsloping'),
            (1, 'Flat'),
            (2, 'Downsloping')
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    ca = forms.IntegerField(
        label='Number of Major Vessels Colored by Fluoroscopy',
        min_value=0, max_value=4,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    thal = forms.ChoiceField(
        choices=[
            (0, 'Normal'),
            (1, 'Fixed Defect'),
            (2, 'Reversible Defect'),
            (3, 'Not Described')
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class KidneyDiseasePredictionForm(forms.Form):
    """Form for kidney disease prediction."""
    
    age = forms.IntegerField(
        min_value=0, max_value=120,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    blood_pressure = forms.IntegerField(
        min_value=0, max_value=300,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    specific_gravity = forms.FloatField(
        min_value=1.000, max_value=1.050,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'})
    )
    albumin = forms.IntegerField(
        min_value=0, max_value=5,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    sugar = forms.IntegerField(
        min_value=0, max_value=5,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    red_blood_cells = forms.ChoiceField(
        choices=[(0, 'Normal'), (1, 'Abnormal')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    pus_cell = forms.ChoiceField(
        choices=[(0, 'Normal'), (1, 'Abnormal')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    pus_cell_clumps = forms.ChoiceField(
        choices=[(0, 'Not Present'), (1, 'Present')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    bacteria = forms.ChoiceField(
        choices=[(0, 'Not Present'), (1, 'Present')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    blood_glucose_random = forms.FloatField(
        min_value=0, max_value=500,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'})
    )
    blood_urea = forms.FloatField(
        min_value=0, max_value=200,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'})
    )
    serum_creatinine = forms.FloatField(
        min_value=0, max_value=20,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    sodium = forms.FloatField(
        min_value=100, max_value=200,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'})
    )
    potassium = forms.FloatField(
        min_value=0, max_value=10,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'})
    )
    hemoglobin = forms.FloatField(
        min_value=0, max_value=20,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'})
    )
    packed_cell_volume = forms.IntegerField(
        min_value=0, max_value=100,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    white_blood_cell_count = forms.IntegerField(
        min_value=0, max_value=50000,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    red_blood_cell_count = forms.FloatField(
        min_value=0, max_value=10,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'})
    )
    hypertension = forms.ChoiceField(
        choices=[(0, 'No'), (1, 'Yes')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    diabetes_mellitus = forms.ChoiceField(
        choices=[(0, 'No'), (1, 'Yes')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    coronary_artery_disease = forms.ChoiceField(
        choices=[(0, 'No'), (1, 'Yes')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    appetite = forms.ChoiceField(
        choices=[(0, 'Good'), (1, 'Poor')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    pedal_edema = forms.ChoiceField(
        choices=[(0, 'No'), (1, 'Yes')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    anemia = forms.ChoiceField(
        choices=[(0, 'No'), (1, 'Yes')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class ParkinsonPredictionForm(forms.Form):
    """Form for Parkinson disease prediction."""
    
    mdvp_fo = forms.FloatField(
        label='MDVP:Fo(Hz)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'})
    )
    mdvp_fhi = forms.FloatField(
        label='MDVP:Fhi(Hz)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'})
    )
    mdvp_flo = forms.FloatField(
        label='MDVP:Flo(Hz)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'})
    )
    mdvp_jitter_percent = forms.FloatField(
        label='MDVP:Jitter(%)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    mdvp_jitter_abs = forms.FloatField(
        label='MDVP:Jitter(Abs)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    mdvp_rap = forms.FloatField(
        label='MDVP:RAP',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    mdvp_ppq = forms.FloatField(
        label='MDVP:PPQ',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    jitter_ddp = forms.FloatField(
        label='Jitter:DDP',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    mdvp_shimmer = forms.FloatField(
        label='MDVP:Shimmer',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    mdvp_shimmer_db = forms.FloatField(
        label='MDVP:Shimmer(dB)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'})
    )
    shimmer_apq3 = forms.FloatField(
        label='Shimmer:APQ3',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    shimmer_apq5 = forms.FloatField(
        label='Shimmer:APQ5',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    mdvp_apq = forms.FloatField(
        label='MDVP:APQ',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    shimmer_dda = forms.FloatField(
        label='Shimmer:DDA',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    nhr = forms.FloatField(
        label='NHR',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    hnr = forms.FloatField(
        label='HNR',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'})
    )
    rpde = forms.FloatField(
        label='RPDE',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    dfa = forms.FloatField(
        label='DFA',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    spread1 = forms.FloatField(
        label='spread1',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    spread2 = forms.FloatField(
        label='spread2',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    d2 = forms.FloatField(
        label='D2',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    ppe = forms.FloatField(
        label='PPE',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )


class BreastCancerPredictionForm(forms.Form):
    """Form for breast cancer prediction."""
    
    # Mean values
    radius_mean = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'})
    )
    texture_mean = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'})
    )
    perimeter_mean = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'})
    )
    area_mean = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'})
    )
    smoothness_mean = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    compactness_mean = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    concavity_mean = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    concave_points_mean = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    symmetry_mean = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    fractal_dimension_mean = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    
    # SE values
    radius_se = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    texture_se = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    perimeter_se = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    area_se = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    smoothness_se = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    compactness_se = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    concavity_se = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    concave_points_se = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    symmetry_se = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    fractal_dimension_se = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    
    # Worst values
    radius_worst = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'})
    )
    texture_worst = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'})
    )
    perimeter_worst = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'})
    )
    area_worst = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'})
    )
    smoothness_worst = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    compactness_worst = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    concavity_worst = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    concave_points_worst = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    symmetry_worst = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )
    fractal_dimension_worst = forms.FloatField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'})
    )


class LiverDiseasePredictionForm(forms.Form):
    """Form for liver disease prediction."""
    
    age = forms.IntegerField(
        min_value=0, max_value=120,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    gender = forms.ChoiceField(
        choices=[(0, 'Female'), (1, 'Male')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    total_bilirubin = forms.FloatField(
        min_value=0, max_value=100,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'})
    )
    direct_bilirubin = forms.FloatField(
        min_value=0, max_value=50,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'})
    )
    alkaline_phosphotase = forms.IntegerField(
        min_value=0, max_value=2000,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    alamine_aminotransferase = forms.IntegerField(
        min_value=0, max_value=2000,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    aspartate_aminotransferase = forms.IntegerField(
        min_value=0, max_value=5000,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    total_proteins = forms.FloatField(
        min_value=0, max_value=10,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'})
    )
    albumin = forms.FloatField(
        min_value=0, max_value=10,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'})
    )
    albumin_globulin_ratio = forms.FloatField(
        min_value=0, max_value=5,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'})
    )