/**
 * Strategies Module
 * Handles loading and managing drone scanning strategies
 */

// Global object to store strategies
window.droneStrategies = {};

document.addEventListener('DOMContentLoaded', function() {
    // Load strategies from the JSON file
    loadStrategies();
});

/**
 * Load strategies from the server
 */
async function loadStrategies() {
    try {
        // In a real application, this would be an API call
        // For this demo, we'll use the strategies from drone_strategies.json
        const strategies = {
            "1:1 Ratio": {
                "Area (km²)": "1,000,000",
                "Kw (%)": "100%",
                "Kp (%)": "100%",
                "H (km)": 1000,
                "V (km)": 1000,
                "Total distance traveled (km)": "1,000,000",
                "Drone speed (km/h)": 100,
                "Time needed for the scan (h)": 10000,
                "Time needed for scan (days)": 416.7,
                "Time needed for scan (min)": 600000
            },
            "1:2 Ratio": {
                "Area (km²)": "750,000",
                "Kw (%)": "75%",
                "Kp (%)": "100%",
                "H (km)": 866,
                "V (km)": 866,
                "Total distance traveled (km)": "1,299,000",
                "Drone speed (km/h)": 100,
                "Time needed for the scan (h)": 12990,
                "Time needed for scan (days)": 541.3,
                "Time needed for scan (min)": 779400
            },
            "1:3 Ratio": {
                "Area (km²)": "500,000",
                "Kw (%)": "50%",
                "Kp (%)": "75%",
                "H (km)": 1732,
                "V (km)": 866,
                "Total distance traveled (km)": "1,000,058",
                "Drone speed (km/h)": 100,
                "Time needed for the scan (h)": 10000,
                "Time needed for scan (days)": 416.7,
                "Time needed for scan (min)": 600000
            },
            "1:5 Ratio": {
                "Area (km²)": "300,000",
                "Kw (%)": "30%",
                "Kp (%)": "38%",
                "H (km)": 1732,
                "V (km)": 866,
                "Total distance traveled (km)": "1,000,058",
                "Drone speed (km/h)": 100,
                "Time needed for the scan (h)": 10000,
                "Time needed for scan (days)": 416.7,
                "Time needed for scan (min)": 600000
            },
            "1:10 Ratio": {
                "Area (km²)": "150,000",
                "Kw (%)": "15%",
                "Kp (%)": "20%",
                "H (km)": 1732,
                "V (km)": 866,
                "Total distance traveled (km)": "1,000,058",
                "Drone speed (km/h)": 100,
                "Time needed for the scan (h)": 10000,
                "Time needed for scan (days)": 416.7,
                "Time needed for scan (min)": 600000
            },
            "1:15 Ratio": {
                "Area (km²)": "100,000",
                "Kw (%)": "10%",
                "Kp (%)": "13%",
                "H (km)": 1732,
                "V (km)": 866,
                "Total distance traveled (km)": "1,000,058",
                "Drone speed (km/h)": 100,
                "Time needed for the scan (h)": 10000,
                "Time needed for scan (days)": 416.7,
                "Time needed for scan (min)": 600000
            },
            "1:20 Ratio": {
                "Area (km²)": "75,000",
                "Kw (%)": "8%",
                "Kp (%)": "10%",
                "H (km)": 1732,
                "V (km)": 866,
                "Total distance traveled (km)": "1,000,058",
                "Drone speed (km/h)": 100,
                "Time needed for the scan (h)": 10000,
                "Time needed for scan (days)": 416.7,
                "Time needed for scan (min)": 600000
            }
        };
        
        // Store strategies globally
        window.droneStrategies = strategies;
        
        // Populate the strategy dropdown
        populateStrategyDropdown(strategies);
        
        console.log('Strategies loaded successfully');
    } catch (error) {
        console.error('Error loading strategies:', error);
    }
}

/**
 * Populate the strategy dropdown with available strategies
 * @param {Object} strategies - The strategies object
 */
function populateStrategyDropdown(strategies) {
    const strategySelect = document.getElementById('strategy-select');
    if (!strategySelect) return;
    
    // Clear existing options
    strategySelect.innerHTML = '';
    
    // Add default option
    const defaultOption = document.createElement('option');
    defaultOption.value = '';
    defaultOption.textContent = '-- Select a Strategy --';
    strategySelect.appendChild(defaultOption);
    
    // Add each strategy as an option
    Object.keys(strategies).forEach(strategyName => {
        const option = document.createElement('option');
        option.value = strategyName;
        option.textContent = strategyName;
        
        // Set 1:5 Ratio as default selected
        if (strategyName === '1:5 Ratio') {
            option.selected = true;
        }
        
        strategySelect.appendChild(option);
    });
    
    // Add change event listener
    strategySelect.addEventListener('change', function() {
        const selectedStrategy = this.value;
        updateStrategyInfo(selectedStrategy);
    });
    
    // Trigger change event to show initial strategy info
    const event = new Event('change');
    strategySelect.dispatchEvent(event);
}

/**
 * Update the UI with information about the selected strategy
 * @param {string} strategyName - The name of the selected strategy
 */
function updateStrategyInfo(strategyName) {
    if (!strategyName || !window.droneStrategies[strategyName]) return;
    
    const strategy = window.droneStrategies[strategyName];
    
    // In a real application, you might update a strategy info panel here
    console.log('Selected strategy:', strategyName, strategy);
}