Here’s a clear, attribute‑by‑attribute explanation of the most commonly used features in the **Heart Disease dataset** you’re working with (the combined Cleveland + Hungary dataset example). These are the standard clinical variables used for model training or textual description in most studies.([Medium][1])

---

### **1. age**

The patient’s age in years. This is a continuous numerical value that helps show how risk changes with age. Older age is generally associated with higher cardiovascular risk.([Medium][1])

---

### **2. sex**

Binary indicator for biological sex:

* **0 = female**
* **1 = male**
  This is included because heart disease risk differs between males and females.([Medium][1])

---

### **3. cp (Chest Pain Type)**

Categorical indicator describing the type of chest pain:

* **0 = typical angina** (classic chest pain from exertion)
* **1 = atypical angina** (not classic but heart‑related)
* **2 = non‑anginal pain** (less likely to be heart‑related)
* **3 = asymptomatic** (no chest pain)
  This helps assess how likely symptoms are to be caused by coronary issues.([PMC][2])

---

### **4. trestbps (Resting Blood Pressure)**

Resting systolic blood pressure (in mm Hg) measured at initial exam. Higher values can signal hypertension, which is a risk factor for heart disease.([Medium][3])

---

### **5. chol (Serum Cholesterol)**

Blood cholesterol level in mg/dL. High cholesterol is a recognized risk factor for atherosclerosis and cardiovascular disease.([Medium][3])

---

### **6. fbs (Fasting Blood Sugar)**

Indicates blood sugar level after fasting:

* **0 = fasting blood sugar ≤ 120 mg/dL** (normal)
* **1 = fasting blood sugar > 120 mg/dL** (elevated)
  Elevated fasting glucose can indicate pre‑diabetes or diabetes, a risk factor for heart disease.([Medium][1])

---

### **7. restecg (Resting Electrocardiographic Results)**

Categorical score based on an ECG at rest:

* **0 = normal ECG**
* **1 = ST‑T wave abnormality** (possible ischemia)
* **2 = probable or definite left ventricular hypertrophy**
  These show different electrical patterns that may reflect heart strain.([Medium][1])

---

### **8. thalach (Maximum Heart Rate Achieved)**

The highest heart rate recorded during a stress test. Lower max heart rates during exercise can be a sign of limited cardiac function.([Medium][1])

---

### **9. exang (Exercise‑Induced Angina)**

Shows whether exercise caused angina (chest pain):

* **0 = No**
* **1 = Yes**
  If a patient develops chest discomfort under stress, it supports a heart disease diagnosis.([Medium][1])

---

### **10. oldpeak (ST Depression)**

Measures how much the ST segment dips during exercise relative to rest (numeric). A larger depression usually reflects more cardiac stress or reduced blood flow.([Medium][1])

---

### **11. slope (Slope of Peak ST Segment)**

Describes the shape of ST segment at peak exercise:

* **0 = upsloping** (generally less worrisome)
* **1 = flat**
* **2 = downsloping** (more suggestive of ischemia)
  This feature reflects how the heart responds electrically under stress.([PMC][2])

---

### **12. ca (Number of Major Vessels Colored by Fluoroscopy)**

Number of major blood vessels visible by fluoroscopy (0–3). A higher count often indicates more severe coronary artery disease.([Medium][1])

---

### **13. thal (Thallium Stress Test Result)**

Categorical indicator from a stress test involving thallium:

* **3 = normal**
* **6 = fixed defect** (may indicate scar tissue)
* **7 = reversible defect** (may indicate ischemia)
  This reflects how the blood supply to heart muscle responds to stress.([GitHub][4])

---

### **14. target / num (Heart Disease Outcome)**

This is the prediction label or outcome:

* **0 = no presence of heart disease**
* **1 = presence of heart disease**
