/**
 * Dashboard Page Integration
 * Connects dashboard UI to real backend APIs
 */

// Wait for DOM to load
document.addEventListener('DOMContentLoaded', async () => {
    console.log('✅ Dashboard loaded');
    
    // Check Authentication
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = '/login';
        return;
    }

    // Update UI for logged in user
    updateAuthUI();

    // Load user's ideas from backend
    await loadUserIdeas();
    
    // Load team status
    await loadTeamStatus();

    // Initialize Real-time Collaboration
    if (window.collaborationClient) {
        window.collaborationClient.connect();
        
        // Subscribe to updates
        window.collaborationClient.subscribe((data) => {
            console.log('🔔 Live Update:', data);
            if (data.type === 'idea_update') {
                // Refresh ideas list if an idea was updated
                loadUserIdeas();
            }
        });
    }
});

function updateAuthUI() {
    const navLinks = document.querySelector('nav .flex.items-center.space-x-4');
    if (navLinks) {
        // Replace "Log In" with "Logout"
        const loginBtn = navLinks.querySelector('a[href="/login"]');
        if (loginBtn) {
            loginBtn.textContent = 'Logout';
            loginBtn.href = '#';
            loginBtn.addEventListener('click', (e) => {
                e.preventDefault();
                localStorage.removeItem('access_token');
                localStorage.removeItem('token_type');
                window.location.href = '/login';
            });
        }
    }
}

/**
 * Load and display user's ideas from backend
 */
async function loadUserIdeas() {
    const ideasContainer = document.getElementById('ideas-list');
    if (!ideasContainer) return;

    try {
        ideasContainer.innerHTML = `
            <div class="text-center py-8 text-gray-400">
                <i class="fas fa-spinner fa-spin fa-3x mb-4"></i>
                <p>Loading your ideas...</p>
            </div>
        `;
        
        // Fetch ideas from backend - listIdeas() will extract user_id from JWT automatically
        const ideas = await api.listIdeas();
        
        console.log('📊 Loaded ideas from API:', ideas);
        
        if (ideas.length === 0) {
            ideasContainer.innerHTML = `
                <div class="text-center py-8">
                    <p class="text-gray-400 mb-4">No ideas yet. Start your entrepreneurial journey!</p>
                    <a href="/intake" class="cta-button inline-block text-white font-bold py-3 px-6 rounded-lg">
                        Create Your First Idea
                    </a>
                </div>
            `;
            return;
        }

        // Display ideas (support nested refined_idea)
        ideasContainer.innerHTML = ideas.map(idea => {
            const refined = idea.refined_idea || {};
            const title = refined.idea_title || idea.problem_statement || 'Untitled Idea';
            const feasibility = refined.initial_feasibility_score || idea.initial_feasibility_score || 0;
            const targetUser = refined.target_user || idea.target_users || 'Not specified';
            return `
                <div class="flex items-center justify-between py-3 px-4 bg-black/30 rounded-lg border border-gray-800 hover:border-indigo-500 transition">
                    <div class="flex-1">
                        <p class="font-medium">${title}</p>
                        <div class="flex gap-4 mt-2">
                            <p class="text-gray-400 text-sm">
                                <i class="fas fa-chart-line"></i>
                                Feasibility: ${feasibility.toFixed(1)}/5
                            </p>
                            <p class="text-gray-400 text-sm">
                                <i class="fas fa-users"></i>
                                ${targetUser}
                            </p>
                        </div>
                    </div>
                    <div class="flex gap-2">
                        <a href="/roadmap?idea_id=${idea.id}" class="text-indigo-400 hover:text-indigo-300 px-3 py-1 rounded border border-indigo-500">
                            <i class="fas fa-route"></i> Roadmap
                        </a>
                        <a href="/cofounder?idea_id=${idea.id}" class="text-purple-400 hover:text-purple-300 px-3 py-1 rounded border border-purple-500">
                            <i class="fas fa-users"></i> Cofounders
                        </a>
                    </div>
                </div>`;
        }).join('');

        console.log(`✅ Displayed ${ideas.length} idea(s) on dashboard`);
    } catch (error) {
        console.error('❌ Error loading ideas:', error);
        ideasContainer.innerHTML = `
            <div class="text-center py-8 text-red-400">
                <i class="fas fa-exclamation-triangle fa-3x mb-4"></i>
                <p>Failed to load your ideas. Please try refreshing the page.</p>
            </div>
        `;
    }
}

/**
 * Load team collaboration status
 */
async function loadTeamStatus() {
    try {
        const status = await api.getTeamStatus();
        const statusBadge = document.getElementById('team-status-badge');
        
        if (statusBadge) {
            if (status.active_connections > 0) {
                statusBadge.innerHTML = `
                    <div class="flex items-center gap-2 text-green-400">
                        <div class="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                        ${status.active_connections} team member${status.active_connections > 1 ? 's' : ''} online
                    </div>
                `;
            } else {
                statusBadge.innerHTML = `
                    <div class="text-gray-500">
                        <i class="fas fa-user-slash"></i> No team members online
                    </div>
                `;
            }
        }
    } catch (error) {
        console.error('Error loading team status:', error);
    }
}

/**
 * View idea details in modal
 */
async function viewIdeaDetails(ideaId) {
    try {
        const idea = await api.getIdea(ideaId);
        
        // Create modal
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4';
        modal.innerHTML = `
            <div class="glass-morphism max-w-2xl w-full rounded-2xl p-6 max-h-[80vh] overflow-y-auto">
                <div class="flex justify-between items-start mb-4">
                    <h3 class="text-2xl font-bold">${idea.problem_statement || 'Idea Details'}</h3>
                    <button onclick="this.closest('.fixed').remove()" class="text-gray-400 hover:text-white">
                        <i class="fas fa-times fa-2x"></i>
                    </button>
                </div>
                
                <div class="space-y-4">
                    <div>
                        <h4 class="text-sm font-semibold text-gray-400 mb-2">Problem Statement</h4>
                        <p class="text-white">${idea.problem_statement || 'N/A'}</p>
                    </div>
                    
                    <div>
                        <h4 class="text-sm font-semibold text-gray-400 mb-2">Proposed Solution</h4>
                        <p class="text-white">${idea.proposed_solution || 'N/A'}</p>
                    </div>
                    
                    <div>
                        <h4 class="text-sm font-semibold text-gray-400 mb-2">Target Users</h4>
                        <p class="text-white">${idea.target_users || 'N/A'}</p>
                    </div>
                    
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <h4 class="text-sm font-semibold text-gray-400 mb-2">Feasibility Score</h4>
                            ${api.formatScoreBar(idea.initial_feasibility_score || 0)}
                        </div>
                        <div>
                            <h4 class="text-sm font-semibold text-gray-400 mb-2">Market Score</h4>
                            ${api.formatScoreBar(idea.market_viability_score || 0)}
                        </div>
                    </div>
                    
                    ${idea.suggestions ? `
                        <div>
                            <h4 class="text-sm font-semibold text-gray-400 mb-2">Suggestions</h4>
                            <div class="bg-black/30 rounded-lg p-3 text-sm">
                                ${idea.suggestions}
                            </div>
                        </div>
                    ` : ''}
                </div>
                
                <div class="mt-6 flex gap-3">
                    <a href="/intake?edit=${idea.id}" class="flex-1 text-center bg-indigo-500 hover:bg-indigo-600 text-white py-3 rounded-lg transition">
                        <i class="fas fa-edit"></i> Edit Idea
                    </a>
                    <button onclick="findCofoundersForIdea('${idea.id}')" class="flex-1 bg-purple-500 hover:bg-purple-600 text-white py-3 rounded-lg transition">
                        <i class="fas fa-users"></i> Find Cofounders
                    </button>
                    <button onclick="analyzeIdea('${idea.id}')" class="flex-1 bg-green-500 hover:bg-green-600 text-white py-3 rounded-lg transition">
                        <i class="fas fa-robot"></i> AI Analysis
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    } catch (error) {
        console.error('Error viewing idea:', error);
        alert('Failed to load idea details');
    }
}

/**
 * Trigger AI agent analysis for an idea
 */
async function analyzeIdea(ideaId) {
    try {
        // Get the idea
        const idea = await api.getIdea(ideaId);
        
        // Show loading modal
        const loadingModal = document.createElement('div');
        loadingModal.id = 'analysis-modal';
        loadingModal.className = 'fixed inset-0 bg-black/90 flex items-center justify-center z-50 p-4';
        loadingModal.innerHTML = `
            <div class="glass-morphism max-w-2xl w-full rounded-2xl p-8 text-center">
                <div class="animate-spin text-6xl mb-4">🤖</div>
                <h3 class="text-2xl font-bold mb-2">AI Agent Analyzing...</h3>
                <p class="text-gray-400 mb-6">Our autonomous agent is conducting a comprehensive analysis</p>
                <div class="space-y-2 text-left" id="analysis-progress">
                    <div class="text-gray-500">⏳ Initializing...</div>
                </div>
            </div>
        `;
        document.body.appendChild(loadingModal);
        
        // Update progress
        const progressDiv = document.getElementById('analysis-progress');
        const updateProgress = (message) => {
            progressDiv.innerHTML += `<div class="text-indigo-400">✅ ${message}</div>`;
        };
        
        setTimeout(() => updateProgress('Validating idea...'), 500);
        setTimeout(() => updateProgress('Analyzing market viability...'), 2000);
        setTimeout(() => updateProgress('Identifying team gaps...'), 4000);
        setTimeout(() => updateProgress('Researching funding options...'), 6000);
        setTimeout(() => updateProgress('Checking legal requirements...'), 8000);
        setTimeout(() => updateProgress('Generating comprehensive report...'), 10000);
        
        // Call the agent API
        const result = await api.invokeAgent(idea.raw_idea_text || idea.problem_statement);
        
        // Show results
        loadingModal.innerHTML = `
            <div class="glass-morphism max-w-4xl w-full rounded-2xl p-8 max-h-[80vh] overflow-y-auto">
                <div class="flex justify-between items-start mb-6">
                    <h3 class="text-3xl font-bold">🎯 Agent Analysis Complete!</h3>
                    <button onclick="this.closest('.fixed').remove()" class="text-gray-400 hover:text-white">
                        <i class="fas fa-times fa-2x"></i>
                    </button>
                </div>
                
                <div class="prose prose-invert max-w-none">
                    <pre class="bg-black/50 p-4 rounded-lg overflow-x-auto text-sm">${JSON.stringify(result, null, 2)}</pre>
                </div>
                
                <div class="mt-6">
                    <button onclick="this.closest('.fixed').remove()" class="w-full bg-indigo-500 hover:bg-indigo-600 text-white py-3 rounded-lg transition">
                        Close Report
                    </button>
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Error analyzing idea:', error);
        document.getElementById('analysis-modal')?.remove();
        alert('Analysis failed: ' + error.message);
    }
}

// Make functions global
window.viewIdeaDetails = viewIdeaDetails;
window.analyzeIdea = analyzeIdea;

/**
 * Find cofounders for an idea
 */
window.findCofoundersForIdea = async function(ideaId) {
    try {
        // Get the idea
        const idea = await api.getIdea(ideaId);
        const ideaText = idea.raw_idea_text || idea.problem_statement || idea.proposed_solution;
        
        if (!ideaText || ideaText.length < 20) {
            alert('Idea description is too short to find matches. Please add more details.');
            return;
        }
        
        // Store idea in session for the cofounder page to use
        sessionStorage.setItem('matchingIdea', ideaText);
        sessionStorage.setItem('matchingIdeaTitle', idea.problem_statement || 'Your Idea');
        
        // Redirect to cofounder page
        window.location.href = '/cofounder?autoMatch=true';
        
    } catch (error) {
        console.error('Error triggering cofounder matching:', error);
        alert('Failed to start cofounder search: ' + error.message);
    }
};
