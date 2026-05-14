// static/js/predictions.js

/**
 * MediPredict - Prediction System
 * Handles disease prediction forms and results
 */

class PredictionSystem {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 4;
        this.formData = {};
        this.isLoading = false;
        
        this.init();
    }
    
    init() {
        this.setupPredictionForms();
        this.setupMultiStepForms();
        this.setupResultDisplays();
        this.setupHistoryNavigation();
        this.setupRealTimeValidation();
    }
    
    setupPredictionForms() {
        // Handle prediction form submission
        document.querySelectorAll('.prediction-form').forEach(form => {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.handlePredictionSubmit(form);
            });
        });
        
        // Disease-specific form handling
        this.setupDiseaseSpecificForms();
        
        // File upload handling
        this.setupFileUploads();
    }
    
    setupDiseaseSpecificForms() {
        // Diabetes form
        const diabetesForm = document.getElementById('diabetes-form');
        if (diabetesForm) {
            this.setupDiabetesForm(diabetesForm);
        }
        
        // Heart disease form
        const heartForm = document.getElementById('heart-form');
        if (heartForm) {
            this.setupHeartForm(heartForm);
        }
        
        // Kidney disease form
        const kidneyForm = document.getElementById('kidney-form');
        if (kidneyForm) {
            this.setupKidneyForm(kidneyForm);
        }
        
        // Parkinson's form
        const parkinsonForm = document.getElementById('parkinson-form');
        if (parkinsonForm) {
            this.setupParkinsonForm(parkinsonForm);
        }
        
        // Breast cancer form
        const breastCancerForm = document.getElementById('breast-cancer-form');
        if (breastCancerForm) {
            this.setupBreastCancerForm(breastCancerForm);
        }
        
        // Liver disease form
        const liverForm = document.getElementById('liver-form');
        if (liverForm) {
            this.setupLiverForm(liverForm);
        }
    }
    
    setupDiabetesForm(form) {
        // Calculate BMI automatically
        const heightInput = form.querySelector('[name="height"]');
        const weightInput = form.querySelector('[name="weight"]');
        const bmiDisplay = form.querySelector('.bmi-display');
        
        if (heightInput && weightInput && bmiDisplay) {
            const calculateBMI = () => {
                const height = parseFloat(heightInput.value) / 100; // cm to m
                const weight = parseFloat(weightInput.value);
                
                if (height && weight) {
                    const bmi = weight / (height * height);
                    bmiDisplay.textContent = bmi.toFixed(1);
                    
                    // Update BMI category
                    const bmiCategory = this.getBMICategory(bmi);
                    bmiDisplay.className = `bmi-display badge ${bmiCategory.class}`;
                    bmiDisplay.title = bmiCategory.label;
                }
            };
            
            heightInput.addEventListener('input', calculateBMI);
            weightInput.addEventListener('input', calculateBMI);
        }
    }
    
    setupHeartForm(form) {
        // Blood pressure validation
        const bpSystolic = form.querySelector('[name="bp_systolic"]');
        const bpDiastolic = form.querySelector('[name="bp_diastolic"]');
        
        if (bpSystolic && bpDiastolic) {
            const validateBP = () => {
                const systolic = parseInt(bpSystolic.value);
                const diastolic = parseInt(bpDiastolic.value);
                
                if (systolic && diastolic) {
                    if (systolic <= diastolic) {
                        this.showFieldError(bpSystolic, 'Systolic must be greater than diastolic');
                    } else {
                        this.clearFieldError(bpSystolic);
                    }
                }
            };
            
            bpSystolic.addEventListener('input', validateBP);
            bpDiastolic.addEventListener('input', validateBP);
        }
    }
    
    setupKidneyForm(form) {
        // eGFR calculation
        const ageInput = form.querySelector('[name="age"]');
        const creatinineInput = form.querySelector('[name="creatinine"]');
        const genderSelect = form.querySelector('[name="gender"]');
        const egfrDisplay = form.querySelector('.egfr-display');
        
        if (ageInput && creatinineInput && genderSelect && egfrDisplay) {
            const calculateEGFR = () => {
                const age = parseInt(ageInput.value);
                const creatinine = parseFloat(creatinineInput.value);
                const gender = genderSelect.value;
                
                if (age && creatinine) {
                    // Simplified eGFR calculation (CKD-EPI formula)
                    let k = gender === 'female' ? 0.7 : 0.9;
                    let a = gender === 'female' ? -0.329 : -0.411;
                    
                    const egfr = 141 * Math.min(creatinine/k, 1) ** a * 
                                Math.max(creatinine/k, 1) ** -1.209 * 
                                0.993 ** age;
                    
                    egfrDisplay.textContent = Math.round(egfr);
                    
                    // Update eGFR category
                    const category = this.getEGFRCategory(egfr);
                    egfrDisplay.className = `egfr-display badge ${category.class}`;
                    egfrDisplay.title = category.label;
                }
            };
            
            ageInput.addEventListener('input', calculateEGFR);
            creatinineInput.addEventListener('input', calculateEGFR);
            genderSelect.addEventListener('change', calculateEGFR);
        }
    }
    
    setupParkinsonForm(form) {
        // Voice analysis file upload
        const voiceFileInput = form.querySelector('[name="voice_sample"]');
        if (voiceFileInput) {
            voiceFileInput.addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (file) {
                    this.validateAudioFile(file);
                }
            });
        }
    }
    
    setupBreastCancerForm(form) {
        // Image preview for mammogram
        const imageInput = form.querySelector('[name="mammogram_image"]');
        const imagePreview = form.querySelector('.image-preview');
        
        if (imageInput && imagePreview) {
            imageInput.addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (file && file.type.startsWith('image/')) {
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        imagePreview.innerHTML = `<img src="${e.target.result}" alt="Mammogram preview">`;
                    };
                    reader.readAsDataURL(file);
                }
            });
        }
    }
    
    setupLiverForm(form) {
        // Liver function test validation
        const bilirubinInput = form.querySelector('[name="bilirubin"]');
        const albuminInput = form.querySelector('[name="albumin"]');
        const inrInput = form.querySelector('[name="inr"]');
        
        if (bilirubinInput && albuminInput && inrInput) {
            const validateLiverValues = () => {
                const bilirubin = parseFloat(bilirubinInput.value);
                const albumin = parseFloat(albuminInput.value);
                const inr = parseFloat(inrInput.value);
                
                if (bilirubin > 20) {
                    this.showFieldError(bilirubinInput, 'Bilirubin level is critically high');
                } else {
                    this.clearFieldError(bilirubinInput);
                }
                
                if (albumin < 2.5) {
                    this.showFieldError(albuminInput, 'Albumin level is critically low');
                } else {
                    this.clearFieldError(albuminInput);
                }
            };
            
            bilirubinInput.addEventListener('input', validateLiverValues);
            albuminInput.addEventListener('input', validateLiverValues);
            inrInput.addEventListener('input', validateLiverValues);
        }
    }
    
    setupMultiStepForms() {
        // Step navigation
        document.querySelectorAll('.next-step').forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                this.goToNextStep();
            });
        });
        
        document.querySelectorAll('.prev-step').forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                this.goToPreviousStep();
            });
        });
        
        // Step indicator clicks
        document.querySelectorAll('.step').forEach((step, index) => {
            step.addEventListener('click', () => {
                if (index < this.currentStep) {
                    this.goToStep(index + 1);
                }
            });
        });
    }
    
    setupResultDisplays() {
        // Handle prediction result display
        const resultContainer = document.getElementById('prediction-result');
        if (resultContainer) {
            this.displayPredictionResult(resultContainer);
        }
        
        // Handle result sharing
        this.setupResultSharing();
        
        // Handle result printing
        this.setupResultPrinting();
    }
    
    setupHistoryNavigation() {
        // Prediction history pagination
        document.querySelectorAll('.history-pagination .page-link').forEach(link => {
            link.addEventListener('click', async (e) => {
                e.preventDefault();
                const page = link.dataset.page;
                await this.loadPredictionHistory(page);
            });
        });
        
        // Prediction detail modal
        document.querySelectorAll('.view-prediction-detail').forEach(button => {
            button.addEventListener('click', async (e) => {
                e.preventDefault();
                const predictionId = button.dataset.id;
                await this.showPredictionDetail(predictionId);
            });
        });
    }
    
    setupRealTimeValidation() {
        // Real-time form validation
        document.querySelectorAll('.prediction-form .form-control').forEach(input => {
            input.addEventListener('input', () => {
                this.validateField(input);
            });
            
            input.addEventListener('blur', () => {
                this.validateField(input, true);
            });
        });
        
        // Range slider value display
        document.querySelectorAll('input[type="range"]').forEach(slider => {
            const valueDisplay = slider.nextElementSibling;
            if (valueDisplay && valueDisplay.classList.contains('range-value')) {
                slider.addEventListener('input', () => {
                    valueDisplay.textContent = slider.value;
                });
            }
        });
    }
    
    setupFileUploads() {
        document.querySelectorAll('.file-upload-area').forEach(area => {
            const input = area.querySelector('input[type="file"]');
            const preview = area.querySelector('.file-preview');
            const message = area.querySelector('.upload-message');
            
            if (!input) return;
            
            // Click to upload
            area.addEventListener('click', () => input.click());
            
            // Drag and drop
            area.addEventListener('dragover', (e) => {
                e.preventDefault();
                area.classList.add('dragover');
            });
            
            area.addEventListener('dragleave', () => {
                area.classList.remove('dragover');
            });
            
            area.addEventListener('drop', (e) => {
                e.preventDefault();
                area.classList.remove('dragover');
                
                if (e.dataTransfer.files.length) {
                    input.files = e.dataTransfer.files;
                    this.handleFileUpload(input.files[0], preview, message);
                }
            });
            
            // File selection
            input.addEventListener('change', () => {
                if (input.files.length) {
                    this.handleFileUpload(input.files[0], preview, message);
                }
            });
        });
    }
    
    async handlePredictionSubmit(form) {
        if (this.isLoading) return;
        
        this.isLoading = true;
        this.showLoading(form);
        
        try {
            // Validate form
            if (!this.validateForm(form)) {
                throw new Error('Please fix the errors in the form');
            }
            
            // Collect form data
            const formData = this.collectFormData(form);
            const diseaseType = form.dataset.diseaseType;
            
            // Send prediction request
            const result = await this.submitPrediction(diseaseType, formData);
            
            // Display result
            await this.displayPredictionResult(result);
            
            // Save to history
            await this.saveToPredictionHistory(result);
            
        } catch (error) {
            console.error('Prediction failed:', error);
            this.showError(form, error.message || 'Prediction failed. Please try again.');
        } finally {
            this.isLoading = false;
            this.hideLoading(form);
        }
    }
    
    validateForm(form) {
        let isValid = true;
        
        // Check required fields
        form.querySelectorAll('[required]').forEach(field => {
            if (!field.value.trim()) {
                this.showFieldError(field, 'This field is required');
                isValid = false;
            } else {
                this.clearFieldError(field);
            }
        });
        
        // Validate number ranges
        form.querySelectorAll('input[type="number"]').forEach(field => {
            if (field.value) {
                const value = parseFloat(field.value);
                const min = parseFloat(field.min);
                const max = parseFloat(field.max);
                
                if (!isNaN(min) && value < min) {
                    this.showFieldError(field, `Value must be at least ${min}`);
                    isValid = false;
                }
                
                if (!isNaN(max) && value > max) {
                    this.showFieldError(field, `Value must be at most ${max}`);
                    isValid = false;
                }
            }
        });
        
        // Validate file uploads
        form.querySelectorAll('input[type="file"]').forEach(field => {
            if (field.hasAttribute('required') && !field.files.length) {
                this.showFieldError(field, 'Please upload a file');
                isValid = false;
            }
        });
        
        return isValid;
    }
    
    validateField(field, showError = false) {
        let isValid = true;
        let errorMessage = '';
        
        // Required validation
        if (field.hasAttribute('required') && !field.value.trim()) {
            isValid = false;
            errorMessage = 'This field is required';
        }
        
        // Email validation
        if (field.type === 'email' && field.value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(field.value)) {
                isValid = false;
                errorMessage = 'Please enter a valid email address';
            }
        }
        
        // Number validation
        if (field.type === 'number' && field.value) {
            const value = parseFloat(field.value);
            const min = parseFloat(field.min);
            const max = parseFloat(field.max);
            
            if (!isNaN(min) && value < min) {
                isValid = false;
                errorMessage = `Value must be at least ${min}`;
            }
            
            if (!isNaN(max) && value > max) {
                isValid = false;
                errorMessage = `Value must be at most ${max}`;
            }
        }
        
        // Pattern validation
        if (field.hasAttribute('pattern') && field.value) {
            const pattern = new RegExp(field.getAttribute('pattern'));
            if (!pattern.test(field.value)) {
                isValid = false;
                errorMessage = field.getAttribute('data-pattern-error') || 'Invalid format';
            }
        }
        
        // Update field state
        if (showError || !isValid) {
            if (!isValid) {
                this.showFieldError(field, errorMessage);
            } else {
                this.clearFieldError(field);
            }
        }
        
        return isValid;
    }
    
    showFieldError(field, message) {
        const formGroup = field.closest('.form-group');
        if (!formGroup) return;
        
        // Remove existing error
        this.clearFieldError(field);
        
        // Add error class
        field.classList.add('is-invalid');
        
        // Add error message
        const errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        errorDiv.textContent = message;
        formGroup.appendChild(errorDiv);
        
        // Scroll to error if it's the first one
        if (!formGroup.querySelector('.is-invalid')) {
            field.scrollIntoView({
                behavior: 'smooth',
                block: 'center'
            });
        }
    }
    
    clearFieldError(field) {
        const formGroup = field.closest('.form-group');
        if (!formGroup) return;
        
        // Remove error class
        field.classList.remove('is-invalid');
        
        // Remove error messages
        formGroup.querySelectorAll('.invalid-feedback').forEach(error => {
            error.remove();
        });
    }
    
    collectFormData(form) {
        const formData = new FormData(form);
        const data = {};
        
        // Convert FormData to object
        for (let [key, value] of formData.entries()) {
            // Handle multiple values (like checkboxes)
            if (data[key]) {
                if (Array.isArray(data[key])) {
                    data[key].push(value);
                } else {
                    data[key] = [data[key], value];
                }
            } else {
                data[key] = value;
            }
        }
        
        // Process file data
        form.querySelectorAll('input[type="file"]').forEach(input => {
            if (input.files.length) {
                // For files, we'll send them separately
                data[input.name] = input.files[0];
            }
        });
        
        return data;
    }
    
    async submitPrediction(diseaseType, data) {
        // Show loading state
        this.showGlobalLoading();
        
        try {
            // API endpoint
            const endpoint = `/api/v1/predict/${diseaseType}/`;
            
            // Prepare form data
            const formData = new FormData();
            
            // Append regular fields
            Object.entries(data).forEach(([key, value]) => {
                if (value instanceof File) {
                    formData.append(key, value);
                } else if (Array.isArray(value)) {
                    value.forEach(v => formData.append(key, v));
                } else {
                    formData.append(key, value);
                }
            });
            
            // Add CSRF token
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
            if (csrfToken) {
                formData.append('csrfmiddlewaretoken', csrfToken);
            }
            
            // Send request
            const response = await fetch(endpoint, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.message || 'Prediction failed');
            }
            
            return result;
            
        } finally {
            this.hideGlobalLoading();
        }
    }
    
    async displayPredictionResult(result) {
        // Create result modal
        const modal = this.createResultModal(result);
        document.body.appendChild(modal);
        
        // Show modal
        this.showModal(modal);
        
        // Setup modal interactions
        this.setupResultModalInteractions(modal, result);
    }
    
    createResultModal(result) {
        const modal = document.createElement('div');
        modal.className = 'modal fade show';
        modal.style.display = 'block';
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Prediction Result</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="prediction-result">
                            <div class="result-header ${result.prediction === 'Positive' ? 'bg-danger' : 'bg-success'}">
                                <h4>${result.disease_type.replace('_', ' ').toUpperCase()} PREDICTION</h4>
                                <p class="mb-0">${result.created_at}</p>
                            </div>
                            <div class="result-body">
                                <div class="row">
                                    <div class="col-md-6">
                                        <div class="result-card">
                                            <h6>Prediction</h6>
                                            <h3 class="${result.prediction === 'Positive' ? 'text-danger' : 'text-success'}">
                                                ${result.prediction}
                                            </h3>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="result-card">
                                            <h6>Confidence</h6>
                                            <h3>${(result.probability * 100).toFixed(1)}%</h3>
                                            <div class="progress" style="height: 10px;">
                                                <div class="progress-bar ${result.prediction === 'Positive' ? 'bg-danger' : 'bg-success'}" 
                                                     style="width: ${result.probability * 100}%"></div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                                ${result.recommendations ? `
                                <div class="recommendations mt-4">
                                    <h5>Recommendations</h5>
                                    <ul class="list-group">
                                        ${result.recommendations.map(rec => `
                                            <li class="list-group-item">${rec}</li>
                                        `).join('')}
                                    </ul>
                                </div>
                                ` : ''}
                                
                                <div class="parameters mt-4">
                                    <h5>Parameters Used</h5>
                                    <div class="table-responsive">
                                        <table class="table table-sm">
                                            <tbody>
                                                ${Object.entries(result.parameters_used || {}).map(([key, value]) => `
                                                    <tr>
                                                        <td><strong>${key.replace(/_/g, ' ')}</strong></td>
                                                        <td>${value}</td>
                                                    </tr>
                                                `).join('')}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        <button type="button" class="btn btn-primary print-result">Print Result</button>
                        <button type="button" class="btn btn-success save-result">Save to History</button>
                    </div>
                </div>
            </div>
        `;
        
        return modal;
    }
    
    setupResultModalInteractions(modal, result) {
        // Close button
        modal.querySelector('.btn-close').addEventListener('click', () => {
            this.hideModal(modal);
        });
        
        // Print button
        modal.querySelector('.print-result').addEventListener('click', () => {
            this.printResult(result);
        });
        
        // Save button
        modal.querySelector('.save-result').addEventListener('click', async () => {
            await this.saveToPredictionHistory(result);
            this.showToast('Result saved to history', 'success');
        });
        
        // Close on backdrop click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.hideModal(modal);
            }
        });
        
        // Close on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.hideModal(modal);
            }
        });
    }
    
    async saveToPredictionHistory(result) {
        try {
            const response = await fetch('/api/v1/predictions/save/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value
                },
                body: JSON.stringify(result)
            });
            
            if (!response.ok) {
                throw new Error('Failed to save prediction');
            }
            
            return await response.json();
        } catch (error) {
            console.error('Error saving prediction:', error);
            throw error;
        }
    }
    
    async loadPredictionHistory(page = 1) {
        try {
            const response = await fetch(`/api/v1/user/predictions/?page=${page}`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to load prediction history');
            }
            
            const data = await response.json();
            this.updateHistoryDisplay(data);
            
        } catch (error) {
            console.error('Error loading prediction history:', error);
            this.showToast('Failed to load prediction history', 'danger');
        }
    }
    
    updateHistoryDisplay(data) {
        const historyContainer = document.getElementById('prediction-history');
        if (!historyContainer) return;
        
        // Update history list
        historyContainer.innerHTML = data.predictions.map(prediction => `
            <div class="prediction-history-item">
                <div class="history-item-header">
                    <h6>${prediction.disease_type.replace('_', ' ').toUpperCase()}</h6>
                    <span class="badge ${prediction.prediction === 'Positive' ? 'bg-danger' : 'bg-success'}">
                        ${prediction.prediction}
                    </span>
                </div>
                <div class="history-item-body">
                    <p>Date: ${new Date(prediction.created_at).toLocaleDateString()}</p>
                    <p>Confidence: ${(prediction.probability * 100).toFixed(1)}%</p>
                </div>
                <div class="history-item-footer">
                    <button class="btn btn-sm btn-outline-primary view-detail" data-id="${prediction.id}">
                        View Details
                    </button>
                </div>
            </div>
        `).join('');
        
        // Update pagination
        this.updatePagination(data);
        
        // Re-attach event listeners
        this.attachHistoryEventListeners();
    }
    
    updatePagination(data) {
        const paginationContainer = document.querySelector('.history-pagination');
        if (!paginationContainer) return;
        
        paginationContainer.innerHTML = `
            <li class="page-item ${data.current_page === 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="${data.current_page - 1}">Previous</a>
            </li>
            
            ${Array.from({length: data.total_pages}, (_, i) => i + 1).map(page => `
                <li class="page-item ${page === data.current_page ? 'active' : ''}">
                    <a class="page-link" href="#" data-page="${page}">${page}</a>
                </li>
            `).join('')}
            
            <li class="page-item ${data.current_page === data.total_pages ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="${data.current_page + 1}">Next</a>
            </li>
        `;
    }
    
    attachHistoryEventListeners() {
        // View detail buttons
        document.querySelectorAll('.view-detail').forEach(button => {
            button.addEventListener('click', async (e) => {
                e.preventDefault();
                const predictionId = button.dataset.id;
                await this.showPredictionDetail(predictionId);
            });
        });
        
        // Pagination links
        document.querySelectorAll('.history-pagination .page-link').forEach(link => {
            link.addEventListener('click', async (e) => {
                e.preventDefault();
                const page = link.dataset.page;
                await this.loadPredictionHistory(page);
            });
        });
    }
    
    async showPredictionDetail(predictionId) {
        try {
            const response = await fetch(`/api/v1/user/predictions/${predictionId}/`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to load prediction details');
            }
            
            const prediction = await response.json();
            this.displayPredictionResult(prediction);
            
        } catch (error) {
            console.error('Error loading prediction detail:', error);
            this.showToast('Failed to load prediction details', 'danger');
        }
    }
    
    setupResultSharing() {
        // Share via email
        document.querySelectorAll('.share-email').forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                this.shareViaEmail();
            });
        });
        
        // Share via social media
        document.querySelectorAll('.share-social').forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                const platform = button.dataset.platform;
                this.shareViaSocial(platform);
            });
        });
        
        // Copy result link
        document.querySelectorAll('.copy-link').forEach(button => {
            button.addEventListener('click', async (e) => {
                e.preventDefault();
                await this.copyResultLink();
            });
        });
    }
    
    setupResultPrinting() {
        document.querySelectorAll('.print-result').forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                this.printCurrentResult();
            });
        });
    }
    
    async shareViaEmail() {
        const result = this.getCurrentResult();
        if (!result) return;
        
        const subject = encodeURIComponent(`MediPredict Result: ${result.disease_type}`);
        const body = encodeURIComponent(`
Prediction Result:
Disease: ${result.disease_type}
Result: ${result.prediction}
Confidence: ${(result.probability * 100).toFixed(1)}%
Date: ${result.created_at}

Recommendations:
${result.recommendations?.join('\n') || 'No specific recommendations'}
        `);
        
        window.location.href = `mailto:?subject=${subject}&body=${body}`;
    }
    
    shareViaSocial(platform) {
        const result = this.getCurrentResult();
        if (!result) return;
        
        const text = encodeURIComponent(`My ${result.disease_type} prediction result: ${result.prediction} with ${(result.probability * 100).toFixed(1)}% confidence`);
        const url = encodeURIComponent(window.location.href);
        
        const urls = {
            twitter: `https://twitter.com/intent/tweet?text=${text}&url=${url}`,
            facebook: `https://www.facebook.com/sharer/sharer.php?u=${url}`,
            linkedin: `https://www.linkedin.com/shareArticle?mini=true&url=${url}&title=${encodeURIComponent('MediPredict Result')}&summary=${text}`,
            whatsapp: `https://api.whatsapp.com/send?text=${text}%20${url}`
        };
        
        if (urls[platform]) {
            window.open(urls[platform], '_blank', 'width=600,height=400');
        }
    }
    
    async copyResultLink() {
        try {
            await navigator.clipboard.writeText(window.location.href);
            this.showToast('Link copied to clipboard', 'success');
        } catch (error) {
            console.error('Failed to copy link:', error);
            this.showToast('Failed to copy link', 'danger');
        }
    }
    
    printCurrentResult() {
        const result = this.getCurrentResult();
        if (!result) return;
        
        const printWindow = window.open('', '_blank');
        printWindow.document.write(`
            <html>
                <head>
                    <title>MediPredict Result - ${result.disease_type}</title>
                    <style>
                        body { font-family: Arial, sans-serif; padding: 20px; }
                        .header { text-align: center; margin-bottom: 30px; }
                        .result { margin: 20px 0; }
                        .recommendations { margin-top: 30px; }
                        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                        th { background-color: #f2f2f2; }
                        .positive { color: #dc3545; }
                        .negative { color: #28a745; }
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h1>MediPredict Disease Prediction</h1>
                        <h2>${result.disease_type.replace('_', ' ').toUpperCase()}</h2>
                        <p>Generated: ${result.created_at}</p>
                    </div>
                    
                    <div class="result">
                        <h3 class="${result.prediction.toLowerCase()}">Prediction: ${result.prediction}</h3>
                        <p><strong>Confidence:</strong> ${(result.probability * 100).toFixed(1)}%</p>
                    </div>
                    
                    ${result.recommendations ? `
                    <div class="recommendations">
                        <h3>Recommendations</h3>
                        <ul>
                            ${result.recommendations.map(rec => `<li>${rec}</li>`).join('')}
                        </ul>
                    </div>
                    ` : ''}
                    
                    <div class="parameters">
                        <h3>Parameters Used</h3>
                        <table>
                            <thead>
                                <tr>
                                    <th>Parameter</th>
                                    <th>Value</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${Object.entries(result.parameters_used || {}).map(([key, value]) => `
                                    <tr>
                                        <td>${key.replace(/_/g, ' ')}</td>
                                        <td>${value}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                    
                    <script>
                        window.onload = function() {
                            window.print();
                            window.onafterprint = function() {
                                window.close();
                            };
                        };
                    </script>
                </body>
            </html>
        `);
        printWindow.document.close();
    }
    
    getCurrentResult() {
        // This should be implemented to get the current result from the DOM or state
        const resultElement = document.querySelector('.prediction-result');
        if (!resultElement) return null;
        
        // Extract data from the DOM
        // This is a simplified implementation
        return {
            disease_type: resultElement.querySelector('.disease-type')?.textContent || '',
            prediction: resultElement.querySelector('.prediction-value')?.textContent || '',
            probability: parseFloat(resultElement.querySelector('.confidence-value')?.textContent || '0') / 100,
            created_at: resultElement.querySelector('.prediction-date')?.textContent || new Date().toISOString(),
            recommendations: Array.from(resultElement.querySelectorAll('.recommendation-item')).map(item => item.textContent),
            parameters_used: {}
        };
    }
    
    // Multi-step form navigation
    goToNextStep() {
        if (this.currentStep < this.totalSteps) {
            const currentStepElement = document.querySelector(`.step-${this.currentStep}`);
            const nextStepElement = document.querySelector(`.step-${this.currentStep + 1}`);
            
            // Validate current step
            if (this.validateStep(this.currentStep)) {
                currentStepElement.classList.remove('active');
                nextStepElement.classList.add('active');
                this.currentStep++;
                this.updateStepIndicator();
                this.scrollToStep();
            }
        }
    }
    
    goToPreviousStep() {
        if (this.currentStep > 1) {
            const currentStepElement = document.querySelector(`.step-${this.currentStep}`);
            const prevStepElement = document.querySelector(`.step-${this.currentStep - 1}`);
            
            currentStepElement.classList.remove('active');
            prevStepElement.classList.add('active');
            this.currentStep--;
            this.updateStepIndicator();
            this.scrollToStep();
        }
    }
    
    goToStep(step) {
        if (step >= 1 && step <= this.totalSteps && step !== this.currentStep) {
            // Validate all steps up to the target step
            let canGoToStep = true;
            for (let i = 1; i < step; i++) {
                if (!this.validateStep(i)) {
                    canGoToStep = false;
                    break;
                }
            }
            
            if (canGoToStep) {
                document.querySelectorAll('.form-step').forEach(stepEl => {
                    stepEl.classList.remove('active');
                });
                
                document.querySelector(`.step-${step}`).classList.add('active');
                this.currentStep = step;
                this.updateStepIndicator();
                this.scrollToStep();
            }
        }
    }
    
    validateStep(step) {
        const stepElement = document.querySelector(`.step-${step}`);
        let isValid = true;
        
        // Validate all required fields in this step
        stepElement.querySelectorAll('[required]').forEach(field => {
            if (!field.value.trim()) {
                this.showFieldError(field, 'This field is required');
                isValid = false;
            }
        });
        
        return isValid;
    }
    
    updateStepIndicator() {
        document.querySelectorAll('.step').forEach((step, index) => {
            const stepNumber = index + 1;
            
            step.classList.remove('active', 'completed');
            
            if (stepNumber === this.currentStep) {
                step.classList.add('active');
            } else if (stepNumber < this.currentStep) {
                step.classList.add('completed');
            }
        });
    }
    
    scrollToStep() {
        const stepElement = document.querySelector(`.step-${this.currentStep}`);
        if (stepElement) {
            stepElement.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    }
    
    // File upload handling
    async handleFileUpload(file, previewElement, messageElement) {
        if (!this.validateFile(file)) {
            if (messageElement) {
                messageElement.textContent = 'Invalid file type or size';
                messageElement.style.color = '#dc3545';
            }
            return;
        }
        
        if (previewElement) {
            if (file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    previewElement.innerHTML = `<img src="${e.target.result}" alt="Preview">`;
                };
                reader.readAsDataURL(file);
            } else if (file.type.startsWith('audio/')) {
                previewElement.innerHTML = `
                    <div class="audio-preview">
                        <i class="fas fa-music"></i>
                        <p>${file.name}</p>
                    </div>
                `;
            } else {
                previewElement.innerHTML = `
                    <div class="file-preview">
                        <i class="fas fa-file"></i>
                        <p>${file.name}</p>
                        <p class="file-size">${this.formatFileSize(file.size)}</p>
                    </div>
                `;
            }
        }
        
        if (messageElement) {
            messageElement.textContent = `File "${file.name}" uploaded successfully`;
            messageElement.style.color = '#28a745';
        }
    }
    
    validateFile(file) {
        // Check file type
        const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'audio/wav', 'audio/mp3', 'application/pdf'];
        if (!allowedTypes.includes(file.type)) {
            return false;
        }
        
        // Check file size (max 10MB)
        const maxSize = 10 * 1024 * 1024; // 10MB in bytes
        if (file.size > maxSize) {
            return false;
        }
        
        return true;
    }
    
    validateAudioFile(file) {
        const allowedAudioTypes = ['audio/wav', 'audio/mp3', 'audio/mpeg'];
        
        if (!allowedAudioTypes.includes(file.type)) {
            this.showToast('Please upload a valid audio file (WAV or MP3)', 'warning');
            return false;
        }
        
        if (file.size > 5 * 1024 * 1024) { // 5MB limit
            this.showToast('Audio file must be less than 5MB', 'warning');
            return false;
        }
        
        return true;
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    // Utility methods
    getBMICategory(bmi) {
        if (bmi < 18.5) return { class: 'bg-warning', label: 'Underweight' };
        if (bmi < 25) return { class: 'bg-success', label: 'Normal' };
        if (bmi < 30) return { class: 'bg-warning', label: 'Overweight' };
        return { class: 'bg-danger', label: 'Obese' };
    }
    
    getEGFRCategory(egfr) {
        if (egfr >= 90) return { class: 'bg-success', label: 'Normal' };
        if (egfr >= 60) return { class: 'bg-warning', label: 'Mild decrease' };
        if (egfr >= 45) return { class: 'bg-warning', label: 'Mild to moderate' };
        if (egfr >= 30) return { class: 'bg-danger', label: 'Moderate to severe' };
        if (egfr >= 15) return { class: 'bg-danger', label: 'Severe' };
        return { class: 'bg-danger', label: 'Kidney failure' };
    }
    
    showLoading(form) {
        const submitButton = form.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
            submitButton.disabled = true;
        }
        
        // Add overlay
        const overlay = document.createElement('div');
        overlay.className = 'form-loading-overlay';
        form.appendChild(overlay);
    }
    
    hideLoading(form) {
        const submitButton = form.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.innerHTML = 'Submit Prediction';
            submitButton.disabled = false;
        }
        
        // Remove overlay
        const overlay = form.querySelector('.form-loading-overlay');
        if (overlay) {
            overlay.remove();
        }
    }
    
    showGlobalLoading() {
        const loader = document.createElement('div');
        loader.id = 'global-loader';
        loader.className = 'global-loader';
        loader.innerHTML = `
            <div class="loader-content">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-3">Processing prediction...</p>
            </div>
        `;
        document.body.appendChild(loader);
    }
    
    hideGlobalLoading() {
        const loader = document.getElementById('global-loader');
        if (loader) {
            loader.remove();
        }
    }
    
    showError(form, message) {
        // Remove existing error alerts
        form.querySelectorAll('.alert-danger').forEach(alert => alert.remove());
        
        // Create error alert
        const alert = document.createElement('div');
        alert.className = 'alert alert-danger alert-dismissible fade show';
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // Insert at the beginning of the form
        form.insertBefore(alert, form.firstChild);
        
        // Scroll to error
        alert.scrollIntoView({
            behavior: 'smooth',
            block: 'center'
        });
    }
    
    showToast(message, type = 'info', duration = 5000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-body">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        // Show toast
        setTimeout(() => {
            toast.classList.add('show');
        }, 100);
        
        // Auto-remove
        setTimeout(() => {
            this.hideToast(toast);
        }, duration);
        
        // Close button
        toast.querySelector('.btn-close').addEventListener('click', () => {
            this.hideToast(toast);
        });
    }
    
    hideToast(toast) {
        toast.classList.remove('show');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }
    
    showModal(modal) {
        modal.classList.add('show');
        modal.style.display = 'block';
        document.body.classList.add('modal-open');
    }
    
    hideModal(modal) {
        modal.classList.remove('show');
        modal.style.display = 'none';
        document.body.classList.remove('modal-open');
        setTimeout(() => {
            if (modal.parentNode) {
                modal.parentNode.removeChild(modal);
            }
        }, 300);
    }
    
    printResult(result) {
        const printContent = this.generatePrintContent(result);
        const printWindow = window.open('', '_blank');
        
        printWindow.document.write(printContent);
        printWindow.document.close();
        printWindow.focus();
        
        printWindow.onload = function() {
            printWindow.print();
            printWindow.onafterprint = function() {
                printWindow.close();
            };
        };
    }
    
    generatePrintContent(result) {
        return `
            <!DOCTYPE html>
            <html>
                <head>
                    <title>MediPredict Result - ${result.disease_type}</title>
                    <style>
                        body {
                            font-family: Arial, sans-serif;
                            line-height: 1.6;
                            color: #333;
                            max-width: 800px;
                            margin: 0 auto;
                            padding: 20px;
                        }
                        .header {
                            text-align: center;
                            border-bottom: 2px solid #4361ee;
                            padding-bottom: 20px;
                            margin-bottom: 30px;
                        }
                        .header h1 {
                            color: #4361ee;
                            margin-bottom: 10px;
                        }
                        .result-card {
                            background: #f8f9fa;
                            border-radius: 8px;
                            padding: 20px;
                            margin: 20px 0;
                        }
                        .prediction {
                            font-size: 24px;
                            font-weight: bold;
                            margin: 10px 0;
                        }
                        .positive { color: #dc3545; }
                        .negative { color: #28a745; }
                        .confidence-bar {
                            height: 20px;
                            background: #e9ecef;
                            border-radius: 10px;
                            margin: 10px 0;
                            overflow: hidden;
                        }
                        .confidence-fill {
                            height: 100%;
                            border-radius: 10px;
                        }
                        .positive .confidence-fill { background: #dc3545; }
                        .negative .confidence-fill { background: #28a745; }
                        table {
                            width: 100%;
                            border-collapse: collapse;
                            margin: 20px 0;
                        }
                        th, td {
                            border: 1px solid #dee2e6;
                            padding: 12px;
                            text-align: left;
                        }
                        th {
                            background-color: #f8f9fa;
                            font-weight: bold;
                        }
                        .recommendations {
                            margin-top: 30px;
                        }
                        .recommendations ul {
                            padding-left: 20px;
                        }
                        .footer {
                            margin-top: 40px;
                            padding-top: 20px;
                            border-top: 1px solid #dee2e6;
                            text-align: center;
                            color: #6c757d;
                            font-size: 14px;
                        }
                        @media print {
                            .no-print { display: none; }
                            body { font-size: 12pt; }
                        }
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h1>MediPredict Disease Prediction System</h1>
                        <h2>${result.disease_type.replace('_', ' ').toUpperCase()} Prediction Result</h2>
                        <p>Report generated on ${new Date(result.created_at).toLocaleString()}</p>
                    </div>
                    
                    <div class="result-card">
                        <h3>Prediction Summary</h3>
                        <div class="prediction ${result.prediction.toLowerCase()}">
                            ${result.prediction}
                        </div>
                        <p><strong>Confidence Level:</strong> ${(result.probability * 100).toFixed(1)}%</p>
                        <div class="confidence-bar">
                            <div class="confidence-fill ${result.prediction.toLowerCase()}" 
                                 style="width: ${result.probability * 100}%"></div>
                        </div>
                    </div>
                    
                    ${result.recommendations && result.recommendations.length ? `
                    <div class="recommendations">
                        <h3>Recommendations</h3>
                        <ul>
                            ${result.recommendations.map(rec => `<li>${rec}</li>`).join('')}
                        </ul>
                    </div>
                    ` : ''}
                    
                    <div class="parameters">
                        <h3>Input Parameters</h3>
                        <table>
                            <thead>
                                <tr>
                                    <th>Parameter</th>
                                    <th>Value</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${Object.entries(result.parameters_used || {}).map(([key, value]) => `
                                    <tr>
                                        <td>${key.replace(/_/g, ' ')}</td>
                                        <td>${value}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                    
                    <div class="footer">
                        <p>This report is generated by MediPredict Disease Prediction System.</p>
                        <p>For medical advice, please consult with a healthcare professional.</p>
                        <p class="no-print">
                            <button onclick="window.print()" class="btn btn-primary">Print Report</button>
                            <button onclick="window.close()" class="btn btn-secondary">Close</button>
                        </p>
                    </div>
                    
                    <script>
                        window.onload = function() {
                            // Auto-print
                            window.print();
                            
                            // Close after printing
                            window.onafterprint = function() {
                                window.close();
                            };
                        };
                    </script>
                </body>
            </html>
        `;
    }
}

// Initialize prediction system when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.PredictionSystem = new PredictionSystem();
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PredictionSystem;
}