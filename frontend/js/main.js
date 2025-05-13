/**
 * Main JavaScript for the Drone Simulation Portal
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize the simulation form
    initSimulationForm();
    
    // Initialize advanced settings modal
    initAdvancedSettings();
    
    // Handle drone pattern change
    handleDronePatternChange();
});

/**
 * Initialize the simulation form
 */
function initSimulationForm() {
    const form = document.getElementById('simulation-form');
    if (!form) return;
    
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        runSimulation();
    });
}

/**
 * Initialize advanced settings modal
 */
function initAdvancedSettings() {
    const advancedBtn = document.getElementById('advanced-settings-btn');
    if (!advancedBtn) return;
    
    advancedBtn.addEventListener('click', function() {
        const modal = new bootstrap.Modal(document.getElementById('advanced-settings-modal'));
        modal.show();
    });
    
    // Handle particle density slider
    const densitySlider = document.getElementById('particle-density');
    const densityValue = document.getElementById('particle-density-value');
    
    if (densitySlider && densityValue) {
        densitySlider.addEventListener('input', function() {
            densityValue.textContent = this.value;
        });
    }
    
    // Handle save settings button
    const saveBtn = document.getElementById('save-advanced-settings');
    if (saveBtn) {
        saveBtn.addEventListener('click', function() {
            // In a real application, you would save these settings
            // For this demo, we'll just close the modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('advanced-settings-modal'));
            modal.hide();
            
            // Show a success message
            alert('Advanced settings saved!');
        });
    }
}

/**
 * Handle drone pattern change
 */
function handleDronePatternChange() {
    const patternSelect = document.getElementById('drone-pattern');
    const strategySelect = document.getElementById('strategy-select');
    
    if (!patternSelect || !strategySelect) return;
    
    patternSelect.addEventListener('change', function() {
        const pattern = this.value;
        
        // Enable/disable strategy dropdown based on pattern
        if (pattern === 'circular') {
            strategySelect.disabled = true;
            strategySelect.parentElement.classList.add('text-muted');
        } else {
            strategySelect.disabled = false;
            strategySelect.parentElement.classList.remove('text-muted');
        }
    });
    
    // Trigger change event to set initial state
    const event = new Event('change');
    patternSelect.dispatchEvent(event);
}

/**
 * Run the simulation with the selected parameters
 */
function runSimulation() {
    // Get form values
    const pattern = document.getElementById('drone-pattern').value;
    const strategy = document.getElementById('strategy-select').value;
    const seed = document.getElementById('random-seed').value;
    const steps = document.getElementById('num-steps').value;
    
    // Show loading state
    const simulationDisplay = document.getElementById('simulation-display');
    simulationDisplay.innerHTML = `
        <div class="text-center">
            <div class="loading-spinner mb-3"></div>
            <p>Running simulation...</p>
        </div>
    `;
    
    // In a real application, this would make an API call to the backend
    // For this demo, we'll simulate a delay and then show a sample result
    setTimeout(() => {
        showSimulationResults(pattern, strategy, seed, steps);
    }, 2000);
}

/**
 * Show simulation results
 * @param {string} pattern - The drone pattern
 * @param {string} strategy - The scanning strategy
 * @param {string} seed - The random seed
 * @param {string} steps - The number of simulation steps
 */
function showSimulationResults(pattern, strategy, seed, steps) {
    // In a real application, this would display actual simulation results
    // For this demo, we'll show a placeholder image and sample stats
    
    // Update the simulation display
    const simulationDisplay = document.getElementById('simulation-display');
    simulationDisplay.innerHTML = `
        <img id="simulation-gif" src="images/sample_simulation.gif" alt="Simulation Animation" class="img-fluid border rounded">
    `;
    
    // Update the statistics panel
    const statsPanel = document.getElementById('simulation-stats');
    if (statsPanel) {
        statsPanel.innerHTML = `
            <table class="table table-sm">
                <tbody>
                    <tr>
                        <th>Pattern:</th>
                        <td>${pattern}</td>
                    </tr>
                    <tr>
                        <th>Strategy:</th>
                        <td>${strategy || 'N/A'}</td>
                    </tr>
                    <tr>
                        <th>Seed:</th>
                        <td>${seed || 'Random'}</td>
                    </tr>
                    <tr>
                        <th>Steps:</th>
                        <td>${steps}</td>
                    </tr>
                    <tr>
                        <th>Particles Detected:</th>
                        <td>1,245.32</td>
                    </tr>
                    <tr>
                        <th>Particles Processed:</th>
                        <td>987.65</td>
                    </tr>
                    <tr>
                        <th>Processing Efficiency:</th>
                        <td>79.3%</td>
                    </tr>
                </tbody>
            </table>
            <div class="d-grid gap-2 mt-3">
                <button class="btn btn-sm btn-outline-primary" type="button">
                    <i class="fas fa-download"></i> Download Results
                </button>
            </div>
        `;
    }
}