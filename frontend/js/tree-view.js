/**
 * Tree View Component
 * Handles the interactive tree view in the sidebar
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tree view
    initTreeView();
    
    // Load strategies into tree view
    loadStrategiesIntoTree();
});

/**
 * Initialize the tree view with toggle functionality
 */
function initTreeView() {
    // Get all tree toggle elements
    const toggles = document.querySelectorAll('.tree-toggle');
    
    // Add click event to each toggle
    toggles.forEach(toggle => {
        // Set initial state for top-level items (expanded)
        if (toggle.parentElement.parentElement.classList.contains('tree-view')) {
            toggle.classList.add('active');
            const childList = toggle.nextElementSibling;
            if (childList && childList.tagName === 'UL') {
                childList.style.display = 'block';
            }
        }
        
        // Add click event listener
        toggle.addEventListener('click', function() {
            this.classList.toggle('active');
            
            // Toggle visibility of child list
            const childList = this.nextElementSibling;
            if (childList && childList.tagName === 'UL') {
                childList.style.display = childList.style.display === 'block' ? 'none' : 'block';
            }
        });
    });
}

/**
 * Load strategies into the tree view
 */
function loadStrategiesIntoTree() {
    const strategiesTree = document.getElementById('strategies-tree');
    
    if (!strategiesTree || !window.droneStrategies) return;
    
    // Clear existing items
    strategiesTree.innerHTML = '';
    
    // Add each strategy to the tree
    Object.keys(window.droneStrategies).forEach(strategyName => {
        const li = document.createElement('li');
        const span = document.createElement('span');
        
        // Create icon element
        const icon = document.createElement('i');
        icon.className = 'fas fa-file-alt';
        
        span.appendChild(icon);
        span.appendChild(document.createTextNode(' ' + strategyName));
        
        // Add click handler to show strategy details
        span.addEventListener('click', function() {
            showStrategyDetails(strategyName);
        });
        
        li.appendChild(span);
        strategiesTree.appendChild(li);
    });
}

/**
 * Show strategy details when clicked in the tree
 * @param {string} strategyName - The name of the strategy to display
 */
function showStrategyDetails(strategyName) {
    if (!window.droneStrategies || !window.droneStrategies[strategyName]) return;
    
    const strategy = window.droneStrategies[strategyName];
    
    // Create modal to show strategy details
    const modalHtml = `
        <div class="modal fade" id="strategy-details-modal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header bg-info text-white">
                        <h5 class="modal-title">Strategy: ${strategyName}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <table class="table table-striped">
                            <tbody>
                                ${Object.entries(strategy).map(([key, value]) => `
                                    <tr>
                                        <th>${key}</th>
                                        <td>${value}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        <button type="button" class="btn btn-primary" onclick="selectStrategy('${strategyName}')">Use This Strategy</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Remove any existing modal
    const existingModal = document.getElementById('strategy-details-modal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add the modal to the document
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('strategy-details-modal'));
    modal.show();
}

/**
 * Select a strategy from the tree view
 * @param {string} strategyName - The name of the strategy to select
 */
function selectStrategy(strategyName) {
    const strategySelect = document.getElementById('strategy-select');
    if (strategySelect) {
        strategySelect.value = strategyName;
        
        // Trigger change event
        const event = new Event('change');
        strategySelect.dispatchEvent(event);
    }
    
    // Close the modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('strategy-details-modal'));
    if (modal) {
        modal.hide();
    }
}