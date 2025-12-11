/**
 * Intake Page Integration
 * Connects idea submission form to Elevare's autonomous agent workflow
 */

// Global blueprint instance
let ideaBlueprint = null;
let crystallizedStructure = null;

// Agent workflow nodes (for progress tracking)
const WORKFLOW_NODES = [
    { id: 'crystallization', name: 'Crystallizing Structure', icon: '💎', description: 'Extracting tech stack, compliance, and talent needs' },
    { id: 'idea_validation', name: 'Validating Idea', icon: '🔍', description: 'AI analyzing feasibility and market fit' },
    { id: 'team_building', name: 'Team Recommendations', icon: '👥', description: 'Identifying required skills and roles' },
    { id: 'funding_analysis', name: 'Funding Strategy', icon: '💰', description: 'Analyzing funding options and requirements' },
    { id: 'legal_compliance', name: 'Legal Requirements', icon: '⚖️', description: 'Checking compliance and regulations' },
    { id: 'market_analysis', name: 'Market Research', icon: '📊', description: 'Deep market analysis via RAG' },
    { id: 'final_report', name: 'Generating Report', icon: '📝', description: 'Compiling comprehensive analysis' }
];

let currentConversationId = null;

/**
 * Initialize the intake page
 */
function initializeIntakePage() {
    const form = document.getElementById('ideaForm');
    if (!form) return;

    form.addEventListener('submit', handleIdeaSubmission);
    setupRealtimeRefinement();
    
    // Create intake particles
    createIntakeParticles();
    
    // Animate form on load
    gsap.fromTo('.intake-card-pro', {
        y: 50,
        opacity: 0,
        scale: 0.95
    }, {
        y: 0,
        opacity: 1,
        scale: 1,
        duration: 0.8,
        ease: 'power3.out',
        delay: 0.2
    });
}

/**
 * Handle idea submission
 */
async function handleIdeaSubmission(e) {
    e.preventDefault();

    // Hide previous results/errors
    document.getElementById('ideaResults')?.classList.add('hidden');
    document.getElementById('ideaError')?.classList.add('hidden');
    document.getElementById('ideaBlueprintContainer')?.classList.add('hidden');

    // Gather form data
    const formData = gatherFormData();
    if (!formData) return;

    // Show progress modal
    showAgentProgressModal();

    try {
        // STEP 1: Crystallize the idea first (get structural blueprint)
        updateProgressNode('crystallization', 'running');
        
        try {
            crystallizedStructure = await crystallizeIdea(formData.rawIdea);
            console.log('💎 Crystallized structure:', crystallizedStructure);
            
            // Initialize and render the blueprint
            if (!ideaBlueprint) {
                ideaBlueprint = new IdeaBlueprint('ideaBlueprintContainer');
            }
            
            // Show the blueprint container
            const blueprintContainer = document.getElementById('ideaBlueprintContainer');
            if (blueprintContainer) {
                blueprintContainer.classList.remove('hidden');
                ideaBlueprint.render(crystallizedStructure);
            }
            
            // Store search queries for use by other components
            window.crystallizedSearchQueries = crystallizedStructure.search_queries;
            
            updateProgressNode('crystallization', 'completed');
        } catch (crystalError) {
            console.warn('Crystallization failed, continuing with agent workflow:', crystalError);
            updateProgressNode('crystallization', 'error');
            crystallizedStructure = null;
        }

        // STEP 2: Call autonomous agent workflow
        const result = await api.invokeAgent(formData.rawIdea, {
            onProgress: updateProgressNode,
            includeMarketProfile: true,
            includeTeamRecommendations: true,
            includeFundingOptions: true,
            includeLegalGuidance: true,
            // Pass crystallized structure to enhance matching accuracy
            crystallizedStructure: crystallizedStructure
        });

        currentConversationId = result.conversation_id;

        // Hide progress modal
        hideAgentProgressModal();

        // Display comprehensive results
        displayAgentResults(result);

        // Save to database
        await saveIdeaToDatabase(result, formData);

        // Scroll to results (after blueprint if shown)
        setTimeout(() => {
            const scrollTarget = crystallizedStructure 
                ? document.getElementById('ideaBlueprintContainer')
                : document.getElementById('ideaResults');
            if (scrollTarget) {
                window.scrollTo({ 
                    top: scrollTarget.offsetTop - 120, 
                    behavior: 'smooth' 
                });
            }
        }, 100);

    } catch (error) {
        console.error('Agent workflow error:', error);
        hideAgentProgressModal();
        showError(error.message || 'Failed to analyze idea. Please try again.');
    }
}

/**
 * Gather form data
 */
function gatherFormData() {
    const description = document.getElementById('ideaDescription')?.value.trim();
    const problem = document.getElementById('problemStatement')?.value.trim();
    const industryElement = document.querySelector('input[name="industry"]:checked');
    const industry = industryElement?.value || 'Other';
    
    const resourceElements = document.querySelectorAll('input[name="resources"]:checked');
    const resources = Array.from(resourceElements).map(el => el.value);

    if (!description || !problem) {
        showError('Please fill in both the idea description and problem statement.');
        return null;
    }

    // Build comprehensive raw idea text for the agent
    const rawIdea = `
IDEA DESCRIPTION:
${description}

PROBLEM STATEMENT:
${problem}

INDUSTRY/DOMAIN:
${industry}

RESOURCES NEEDED:
${resources.length > 0 ? resources.join(', ') : 'Not specified'}
`.trim();

    return {
        rawIdea,
        description,
        problem,
        industry,
        resources
    };
}

/**
 * Setup real-time NLP refinement (debounced calls to /refine-idea)
 */
function setupRealtimeRefinement() {
    const desc = document.getElementById('ideaDescription');
    const prob = document.getElementById('problemStatement');
    if (!desc || !prob) return;

    let debounceTimer = null;
    let lastText = '';
    let inFlight = false;
    let sseSource = null;
    let sseAvailable = typeof window !== 'undefined' && 'EventSource' in window;

    const previewBox = document.getElementById('liveIdeaPreview');
    const statusEl = document.getElementById('livePreviewStatus');
    const contentEl = document.getElementById('livePreviewContent');

    const renderPreview = (fullProfile) => {
        const r = (fullProfile && (fullProfile.refined_idea || fullProfile.refinedIdea)) || {};
        const m = (fullProfile && fullProfile.market_profile) || {};
        if (contentEl) {
            contentEl.innerHTML = `
                <div class="space-y-2">
                    <p><span class="font-semibold text-white">Title:</span> ${r.idea_title || 'Draft Title'}</p>
                    <p class="text-gray-400"><span class="font-semibold text-white">Domain:</span> ${r.core_domain || 'Unknown'}</p>
                    <p class="text-gray-300"><span class="font-semibold text-white">Problem:</span> ${(r.problem_statement || '').slice(0,160) || '—'}</p>
                    <p class="text-gray-300"><span class="font-semibold text-white">Solution:</span> ${(r.solution_concept || '').slice(0,160) || '—'}</p>
                    <div class="flex flex-wrap gap-1 mt-2">${(r.nlp_suggestions || []).slice(0,4).map(s => `<span class='px-2 py-1 bg-yellow-500/20 text-yellow-200 rounded text-xs'>${s}</span>`).join('')}</div>
                    <p class="text-xs text-gray-500">Feasibility: ${r.initial_feasibility_score ?? '—'} • Market Score: ${m.market_viability_score ?? '—'}</p>
                </div>`;
        }
    };

    const closeSSE = () => { if (sseSource) { try { sseSource.close(); } catch(_) {} sseSource = null; } };

    const startSSE = (text) => {
        closeSSE();
        if (!previewBox.classList.contains('hidden')) {
            // keep visible
        } else {
            previewBox.classList.remove('hidden');
        }
        if (statusEl) statusEl.textContent = 'Live (streaming)';
        if (contentEl) contentEl.innerHTML = '<div class="text-yellow-300 flex items-center gap-2"><i class="fas fa-spinner fa-spin"></i><span>Refining...</span></div>';
        try {
            const url = `/refine-idea/stream?text=${encodeURIComponent(text)}`;
            sseSource = new EventSource(url);
            let partial = {};
            sseSource.onmessage = (ev) => {
                try {
                    const data = JSON.parse(ev.data);
                    if (data.type === 'partial' && data.refined_idea) {
                        renderPreview({ refined_idea: data.refined_idea });
                    } else if (data.type === 'refined' && data.refined_idea) {
                        partial.refined_idea = data.refined_idea;
                        renderPreview(partial);
                    } else if (data.type === 'market' && data.market_profile) {
                        partial.market_profile = data.market_profile;
                        renderPreview(partial);
                    } else if (data.type === 'overall') {
                        // optional: show overall score somewhere
                    } else if (data.type === 'done' && data.result) {
                        renderPreview(data.result);
                        if (statusEl) statusEl.textContent = 'Live';
                        closeSSE();
                    } else if (data.type === 'status') {
                        // keep status visible
                    } else if (data.type === 'error') {
                        if (statusEl) statusEl.textContent = 'Error (stream)';
                        closeSSE();
                        // Fallback to single-shot refine
                        triggerFallback();
                    }
                } catch (e) {
                    // ignore parse errors
                }
            };
            sseSource.onerror = () => {
                if (statusEl) statusEl.textContent = 'Error (stream)';
                closeSSE();
                triggerFallback();
            };
        } catch (e) {
            if (statusEl) statusEl.textContent = 'Error (stream init)';
            closeSSE();
            triggerFallback();
        }
    };

    const triggerFallback = async () => {
        const text = `${desc.value}\n\nProblem: ${prob.value}`.trim();
        if (text.length < 25 || text === lastText || inFlight) return;
        lastText = text;
        inFlight = true;
        if (previewBox) previewBox.classList.remove('hidden');
        if (statusEl) statusEl.textContent = 'Analyzing...';
        if (contentEl) contentEl.innerHTML = '<div class="text-yellow-300 flex items-center gap-2"><i class="fas fa-spinner fa-spin"></i><span>Refining...</span></div>';
        try {
            const refined = await api.refineIdea(text);
            renderPreview(refined);
            if (statusEl) statusEl.textContent = 'Live';
        } catch (err) {
            console.warn('Realtime refine failed', err);
            if (statusEl) statusEl.textContent = 'Error';
            if (contentEl) contentEl.innerHTML = '<p class="text-red-400 text-sm">Realtime refinement failed. Continuing locally.</p>';
        } finally {
            inFlight = false;
        }
    };

    const trigger = () => {
        const text = `${desc.value}\n\nProblem: ${prob.value}`.trim();
        if (text.length < 25 || text === lastText) return;
        lastText = text;
        if (sseAvailable) {
            startSSE(text);
        } else {
            triggerFallback();
        }
    };

    const schedule = () => {
        if (debounceTimer) clearTimeout(debounceTimer);
        debounceTimer = setTimeout(trigger, 800); // 800ms debounce
    };

    desc.addEventListener('input', schedule);
    prob.addEventListener('input', schedule);
}

/**
 * Show agent progress modal
 */
function showAgentProgressModal() {
    const modal = document.createElement('div');
    modal.id = 'agent-progress-modal';
    modal.className = 'fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4';
    modal.innerHTML = `
        <div class="bg-gradient-to-br from-gray-900 to-black border border-yellow-400/30 rounded-3xl p-8 max-w-2xl w-full shadow-2xl">
            <div class="text-center mb-8">
                <div class="inline-flex items-center gap-2 bg-yellow-500/20 border border-yellow-400/30 rounded-full px-4 py-2 mb-4">
                    <div class="w-2 h-2 bg-yellow-400 rounded-full animate-pulse"></div>
                    <span class="text-sm font-medium text-yellow-200">🤖 AI Agent Active</span>
                </div>
                <h2 class="text-3xl font-bold mb-2">
                    <span class="holographic-text-pro">Analyzing Your Idea</span>
                </h2>
                <p class="text-gray-400">Our autonomous agent is running a 6-node workflow...</p>
            </div>

            <!-- Progress nodes -->
            <div class="space-y-4" id="progress-nodes">
                ${WORKFLOW_NODES.map(node => `
                    <div id="node-${node.id}" class="workflow-node p-4 bg-black/40 border border-gray-700 rounded-xl opacity-50 transition-all duration-300">
                        <div class="flex items-start gap-4">
                            <div class="text-3xl mt-1">${node.icon}</div>
                            <div class="flex-1">
                                <div class="flex items-center justify-between mb-2">
                                    <h3 class="font-bold text-white">${node.name}</h3>
                                    <span class="node-status text-xs px-2 py-1 rounded-full bg-gray-700 text-gray-400">Waiting</span>
                                </div>
                                <p class="text-sm text-gray-400">${node.description}</p>
                                <div class="progress-bar-container mt-2 h-1 bg-gray-800 rounded-full overflow-hidden hidden">
                                    <div class="progress-bar h-full bg-gradient-to-r from-yellow-400 to-orange-400 w-0 transition-all duration-500"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>

            <!-- Overall progress -->
            <div class="mt-6 text-center">
                <div class="text-sm text-gray-400 mb-2">
                    <span id="overall-progress-text">Starting workflow...</span>
                </div>
                <div class="h-2 bg-gray-800 rounded-full overflow-hidden">
                    <div id="overall-progress-bar" class="h-full bg-gradient-to-r from-yellow-400 via-orange-400 to-red-400 w-0 transition-all duration-500"></div>
                </div>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // Animate modal entrance
    gsap.from(modal.querySelector('div'), {
        scale: 0.9,
        opacity: 0,
        duration: 0.3,
        ease: 'power2.out'
    });
}

/**
 * Update progress node status
 */
function updateProgressNode(nodeId, status = 'running') {
    const nodeElement = document.getElementById(`node-${nodeId}`);
    if (!nodeElement) return;

    const statusElement = nodeElement.querySelector('.node-status');
    const progressContainer = nodeElement.querySelector('.progress-bar-container');
    const progressBar = nodeElement.querySelector('.progress-bar');

    // Update visual state based on status
    if (status === 'running') {
        nodeElement.classList.remove('opacity-50');
        nodeElement.classList.add('border-yellow-400/50', 'bg-yellow-500/10');
        statusElement.textContent = 'Running...';
        statusElement.className = 'node-status text-xs px-2 py-1 rounded-full bg-yellow-500/20 text-yellow-300 animate-pulse';
        
        // Show and animate progress bar
        progressContainer?.classList.remove('hidden');
        if (progressBar) {
            progressBar.style.width = '70%';
        }
    } else if (status === 'completed') {
        nodeElement.classList.remove('border-yellow-400/50', 'bg-yellow-500/10');
        nodeElement.classList.add('border-green-400/50', 'bg-green-500/10');
        statusElement.textContent = '✓ Complete';
        statusElement.className = 'node-status text-xs px-2 py-1 rounded-full bg-green-500/20 text-green-300';
        
        if (progressBar) {
            progressBar.style.width = '100%';
            progressBar.className = 'progress-bar h-full bg-gradient-to-r from-green-400 to-emerald-400 transition-all duration-500';
        }
    } else if (status === 'error') {
        nodeElement.classList.add('border-red-400/50', 'bg-red-500/10');
        statusElement.textContent = '✗ Error';
        statusElement.className = 'node-status text-xs px-2 py-1 rounded-full bg-red-500/20 text-red-300';
    }

    // Update overall progress
    const completedNodes = document.querySelectorAll('.node-status:contains("✓")').length;
    const totalNodes = WORKFLOW_NODES.length;
    const progress = (completedNodes / totalNodes) * 100;
    
    const overallBar = document.getElementById('overall-progress-bar');
    const overallText = document.getElementById('overall-progress-text');
    
    if (overallBar) overallBar.style.width = `${progress}%`;
    if (overallText) overallText.textContent = `Step ${completedNodes + 1} of ${totalNodes}`;
}

/**
 * Hide agent progress modal
 */
function hideAgentProgressModal() {
    const modal = document.getElementById('agent-progress-modal');
    if (modal) {
        gsap.to(modal, {
            opacity: 0,
            duration: 0.3,
            onComplete: () => modal.remove()
        });
    }
}

/**
 * Display dimensional analysis results (Module 1)
 */
function displayDimensionalAnalysis(dimensions, domain, domainConfidence, overallScore, explanations = {}) {
    if (!dimensions || Object.keys(dimensions).length === 0) return '';
    
    console.log('📊 displayDimensionalAnalysis called');
    console.log('- Explanations parameter:', explanations);
    console.log('- Explanations type:', typeof explanations);
    console.log('- Explanations keys:', Object.keys(explanations));
    
    // Helper function to format dimension labels
    const formatLabel = (key) => {
        return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    };
    
    // Helper function to get score class
    const getScoreClass = (score) => {
        if (score >= 0.8) return 'excellent';
        if (score >= 0.6) return 'good';
        if (score >= 0.4) return 'fair';
        return 'needs-work';
    };
    
    // Helper function to get score color
    const getScoreColor = (score) => {
        if (score >= 0.8) return '#10b981'; // green
        if (score >= 0.6) return '#3b82f6'; // blue
        if (score >= 0.4) return '#f59e0b'; // orange
        return '#ef4444'; // red
    };
    
    // Helper function to get interpretation
    const getInterpretation = (score) => {
        if (score >= 0.8) return { emoji: '🌟', text: 'Excellent potential!', class: 'excellent' };
        if (score >= 0.6) return { emoji: '✅', text: 'Good potential with refinements', class: 'good' };
        if (score >= 0.4) return { emoji: '⚡', text: 'Moderate potential, needs work', class: 'fair' };
        return { emoji: '🔧', text: 'Significant improvements needed', class: 'needs-work' };
    };
    
    const interpretation = getInterpretation(overallScore);
    const overallPercent = Math.round(overallScore * 100);
    
    return `
        <div class="dimensional-analysis-container bg-gradient-to-br from-purple-900/30 to-blue-900/30 border border-purple-400/40 rounded-3xl p-8 mb-6">
            <h3 class="text-2xl font-bold mb-6 flex items-center gap-3">
                <span class="text-3xl">📊</span>
                <span class="holographic-text-pro">8-Dimensional Analysis</span>
            </h3>
            
            <!-- Overall Score Card -->
            <div class="overall-score-card bg-black/40 border border-purple-400/50 rounded-2xl p-6 mb-6 text-center">
                <div class="flex items-center justify-center gap-8">
                    <div class="relative">
                        <svg width="120" height="120" class="transform -rotate-90">
                            <circle cx="60" cy="60" r="50" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="8"/>
                            <circle cx="60" cy="60" r="50" fill="none" stroke="${getScoreColor(overallScore)}" stroke-width="8"
                                    stroke-dasharray="${overallScore * 314} 314" stroke-linecap="round"/>
                        </svg>
                        <div class="absolute inset-0 flex items-center justify-center">
                            <div class="text-center">
                                <div class="text-3xl font-black" style="color: ${getScoreColor(overallScore)}">${overallPercent}%</div>
                            </div>
                        </div>
                    </div>
                    <div class="text-left">
                        <div class="text-4xl mb-2">${interpretation.emoji}</div>
                        <div class="text-xl font-bold text-white mb-1">Overall Score</div>
                        <div class="text-lg text-gray-300">${interpretation.text}</div>
                        ${domain && domain.length > 0 ? `
                            <div class="flex flex-wrap gap-2 mt-3">
                                ${domain.map(d => `
                                    <span class="px-3 py-1 bg-purple-500/30 border border-purple-400/50 rounded-full text-sm font-medium text-purple-200">
                                        ${d}
                                    </span>
                                `).join('')}
                                <span class="px-3 py-1 bg-gray-700/50 rounded-full text-xs text-gray-400">
                                    ${Math.round(domainConfidence * 100)}% confidence
                                </span>
                            </div>
                        ` : ''}
                    </div>
                </div>
            </div>
            
            <!-- Dimensional Scores Grid with XAI -->
            <div class="grid md:grid-cols-2 gap-4">
                ${Object.entries(dimensions).map(([key, value]) => {
                    if (key === 'technical_complexity') {
                        const complexityColors = {
                            'low': '#10b981',
                            'medium': '#f59e0b',
                            'high': '#ef4444'
                        };
                        const explanation = explanations && explanations[key] ? explanations[key] : 'No detailed reasoning available for this metric.';
                        const scoreVal = value === 'low' ? 0.3 : value === 'medium' ? 0.5 : 0.7;
                        return `
                            <div class="analysis-card" data-dimension="${key}" data-title="${formatLabel(key)}" data-explanation="${explanation.replace(/"/g, '&quot;')}" data-score="${scoreVal}">
                                <div class="flex items-center justify-between mb-2">
                                    <span class="font-medium text-gray-300">${formatLabel(key)}</span>
                                    <span class="px-3 py-1 rounded-full text-sm font-bold" 
                                          style="background-color: ${complexityColors[value] || '#6b7280'}20; color: ${complexityColors[value] || '#6b7280'}">
                                        ${value.toUpperCase()}
                                    </span>
                                </div>
                                <button class="explain-btn">
                                    ✨ Explain
                                </button>
                            </div>
                        `;
                    } else {
                        const percent = Math.round(value * 100);
                        const scoreClass = getScoreClass(value);
                        const color = getScoreColor(value);
                        const explanation = explanations && explanations[key] ? explanations[key] : 'No detailed reasoning available for this metric.';
                        return `
                            <div class="analysis-card" data-dimension="${key}" data-title="${formatLabel(key)}" data-explanation="${explanation.replace(/"/g, '&quot;')}" data-score="${value}">
                                <div class="flex items-center justify-between mb-2">
                                    <span class="font-medium text-gray-300">${formatLabel(key)}</span>
                                    <span class="text-sm font-bold" style="color: ${color}">${percent}%</span>
                                </div>
                                <div class="progress-bar-container w-full h-2 bg-gray-800 rounded-full overflow-hidden">
                                    <div class="progress-bar-fill h-full rounded-full transition-all duration-1000 ${scoreClass}" 
                                         style="width: ${percent}%; background-color: ${color}"></div>
                                </div>
                                <button class="explain-btn">
                                    ✨ Explain
                                </button>
                            </div>
                        `;
                    }
                }).join('')}
            </div>
            
            <!-- Strengths & Areas for Improvement -->
            <div class="grid md:grid-cols-2 gap-4 mt-6">
                <div class="bg-green-900/20 border border-green-500/30 rounded-xl p-4">
                    <h4 class="font-bold text-green-400 mb-2 flex items-center gap-2">
                        <span>💪</span> Top Strengths
                    </h4>
                    <ul class="space-y-1 text-sm text-gray-300">
                        ${Object.entries(dimensions)
                            .filter(([key, value]) => typeof value === 'number' && value >= 0.7)
                            .sort((a, b) => b[1] - a[1])
                            .slice(0, 3)
                            .map(([key, value]) => `
                                <li class="flex items-center gap-2">
                                    <span class="text-green-400">✓</span>
                                    <span>${formatLabel(key)} (${Math.round(value * 100)}%)</span>
                                </li>
                            `).join('') || '<li class="text-gray-400 italic">Keep improving all dimensions</li>'}
                    </ul>
                </div>
                <div class="bg-orange-900/20 border border-orange-500/30 rounded-xl p-4">
                    <h4 class="font-bold text-orange-400 mb-2 flex items-center gap-2">
                        <span>🎯</span> Focus Areas
                    </h4>
                    <ul class="space-y-1 text-sm text-gray-300">
                        ${Object.entries(dimensions)
                            .filter(([key, value]) => typeof value === 'number' && value < 0.6)
                            .sort((a, b) => a[1] - b[1])
                            .slice(0, 3)
                            .map(([key, value]) => `
                                <li class="flex items-center gap-2">
                                    <span class="text-orange-400">→</span>
                                    <span>${formatLabel(key)} (${Math.round(value * 100)}%)</span>
                                </li>
                            `).join('') || '<li class="text-gray-400 italic">All dimensions look strong!</li>'}
                    </ul>
                </div>
            </div>
        </div>
    `;
}

/**
 * Display agent analysis results
 */
function displayAgentResults(result) {
    const resultsDiv = document.getElementById('ideaResults');
    if (!resultsDiv) return;

    // Extract data from agent result (fallbacks for non-streaming invoke where keys differ)
    const validation = result.validation_profile || {};
    const refined = result.refined_concept || validation.refined_concept || {};
    // Attempt to synthesize refined concept if absent
    if (Object.keys(refined).length === 0 && typeof validation.raw_response === 'string') {
        refined.idea_title = 'Untitled Idea';
        refined.problem_statement = 'Not available';
        refined.solution_concept = 'Not available';
        refined.core_domain = 'General';
        refined.target_user = 'Not specified';
    }
    const feasibility = result.feasibility_score || refined.initial_feasibility_score || 0;
    const marketProfile = (validation && validation.market_profile) || {};
    // Concept Card (12 sections) if provided by backend
    const conceptCard = (validation && validation.concept_card) || result.concept_card || null;
    const conceptCardHTML = conceptCard ? `
            <div class="bg-black/40 border border-emerald-400/30 rounded-2xl p-6">
                <h3 class="text-xl font-bold mb-4 flex items-center gap-2">
                    <span>🗂️</span>
                    <span>Startup Concept Card</span>
                </h3>
                <div class="space-y-3 text-gray-300">
                    <p><span class="font-semibold text-white">1) Title:</span> ${conceptCard.title || ''}</p>
                    <p><span class="font-semibold text-white">2) One-Line Elevator Pitch:</span> ${conceptCard.one_line || ''}</p>
                    <div>
                        <p class="font-semibold text-white mb-1">3) Problem Summary:</p>
                        <p class="text-gray-400 bg-black/30 p-3 rounded-lg">${conceptCard.problem_summary || ''}</p>
                    </div>
                    <p><span class="font-semibold text-white">4) Why Now:</span> ${conceptCard.why_now || ''}</p>
                    <div>
                        <p class="font-semibold text-white mb-1">5) Solution Overview:</p>
                        <p class="text-gray-400 bg-black/30 p-3 rounded-lg">${conceptCard.solution_overview || ''}</p>
                    </div>
                    <div>
                        <p class="font-semibold text-white mb-1">6) Key Features:</p>
                        <ul class="list-disc ml-6 text-gray-300">
                            ${(conceptCard.key_features || []).slice(0,5).map(f => `<li>${f}</li>`).join('')}
                        </ul>
                    </div>
                    <p><span class="font-semibold text-white">7) Target Users:</span> ${conceptCard.target_users || ''}</p>
                    <div>
                        <p class="font-semibold text-white mb-1">8) User Journey (Before → After):</p>
                        <p class="text-gray-400 bg-black/30 p-3 rounded-lg">${conceptCard.user_journey || ''}</p>
                    </div>
                    <div>
                        <p class="font-semibold text-white mb-1">9) Value Proposition:</p>
                        <p class="text-gray-400 bg-black/30 p-3 rounded-lg">${conceptCard.value_proposition || ''}</p>
                    </div>
                    <div>
                        <p class="font-semibold text-white mb-1">10) Differentiation / Unfair Advantage:</p>
                        <p class="text-gray-400 bg-black/30 p-3 rounded-lg">${conceptCard.differentiation || ''}</p>
                    </div>
                    <div>
                        <p class="font-semibold text-white mb-1">11) Business Model Snapshot:</p>
                        <p class="text-gray-400 bg-black/30 p-3 rounded-lg">${conceptCard.business_model || ''}</p>
                    </div>
                    <div>
                        <p class="font-semibold text-white mb-1">12) Future Expansion:</p>
                        <p class="text-gray-400 bg-black/30 p-3 rounded-lg">${conceptCard.future_expansion || ''}</p>
                    </div>
                </div>
            </div>
        ` : '';
    const marketSize = marketProfile.market_size_bucket || 'Unknown';
    const fundingPotential = marketProfile.funding_potential_score || 0;
    const explainability = (validation && validation.explainability) || result.explainability || {};
    const teamRecommendations = result.team_recommendations || [];
    const fundingOptions = result.funding_options || [];
    const legalRequirements = result.legal_requirements || [];
    const suggestions = result.suggestions || [];
    
    // Module 1: Extract dimensional analysis data
    const dimensions = result.dimensions || {};
    const domain = result.domain || [];
    const domainConfidence = result.domain_confidence || 0.0;
    const overallScore = result.overall_score || 0.0;
    const explanations = result.dimension_explanations || {};

    // Debug logging
    console.log('🔍 Dimensional Analysis Data:');
    console.log('- Dimensions:', dimensions);
    console.log('- Explanations:', explanations);
    console.log('- Explanations keys:', Object.keys(explanations));

    // Build comprehensive results HTML with dimensional analysis
    const dimensionalHTML = displayDimensionalAnalysis(dimensions, domain, domainConfidence, overallScore, explanations);
    
    resultsDiv.innerHTML = `
        <div class="mt-8 space-y-6">
            <!-- Success Banner -->
            <div class="bg-gradient-to-r from-green-500/20 to-emerald-500/20 border border-green-400/30 rounded-2xl p-6 text-center">
                <div class="text-4xl mb-2">✨</div>
                <h2 class="text-2xl font-bold text-green-300 mb-2">Analysis Complete!</h2>
                <p class="text-gray-300">Your idea has been comprehensively analyzed by our AI agent</p>
            </div>
            
            <!-- Module 1: Dimensional Analysis -->
            ${dimensionalHTML}

            <!-- Startup Concept Card -->
            ${conceptCardHTML}

            ${!conceptCard ? `
            <!-- Refined Concept (shown when Concept Card unavailable) -->
            <div class="bg-black/40 border border-yellow-400/30 rounded-2xl p-6">
                <h3 class="text-xl font-bold mb-4 flex items-center gap-2">
                    <span>💡</span>
                    <span>Refined Concept</span>
                </h3>
                <div class="space-y-3 text-gray-300">
                    <p><span class="font-semibold text-white">Title:</span> ${refined.idea_title || 'Untitled Idea'}</p>
                    <p><span class="font-semibold text-white">Domain:</span> ${refined.core_domain || 'General'}</p>
                    <p><span class="font-semibold text-white">Target User:</span> ${refined.target_user || 'Not specified'}</p>
                    <div class="mt-4">
                        <p class="font-semibold text-white mb-2">Problem Statement:</p>
                        <p class="text-gray-400 bg-black/30 p-3 rounded-lg">${refined.problem_statement || 'Not available'}</p>
                    </div>
                    <div class="mt-4">
                        <p class="font-semibold text-white mb-2">Solution Concept:</p>
                        <p class="text-gray-400 bg-black/30 p-3 rounded-lg">${refined.solution_concept || 'Not available'}</p>
                    </div>
                </div>
            </div>` : ''}

            <!-- Scores Grid -->
            <div class="grid md:grid-cols-3 gap-4">
                <div class="bg-black/40 border border-purple-400/30 rounded-2xl p-6 text-center">
                    <div class="flex items-center justify-center gap-2 mb-2">
                        <div class="text-3xl">🎯</div>
                        ${explainability && explainability.feasibility_explanation ? `
                        <span class="relative group cursor-help text-gray-400">ⓘ
                            <span class="absolute z-10 hidden group-hover:block -top-1 left-5 w-64 bg-black/80 border border-gray-700 text-xs text-gray-200 p-2 rounded shadow-lg text-left">
                                ${explainability.feasibility_explanation}
                            </span>
                        </span>` : ''}
                    </div>
                    <div class="text-2xl font-bold text-purple-300">${feasibility.toFixed(1)}/5</div>
                    <div class="text-sm text-gray-400 mt-1">Feasibility Score</div>
                    ${api.formatScoreBar(feasibility, 5)}
                </div>
                <div class="bg-black/40 border border-blue-400/30 rounded-2xl p-6 text-center">
                    <div class="flex items-center justify-center gap-2 mb-2">
                        <div class="text-3xl">📊</div>
                        ${marketProfile && marketProfile.market_size_explanation ? `
                        <span class="relative group cursor-help text-gray-400">ⓘ
                            <span class="absolute z-10 hidden group-hover:block -top-1 left-5 w-64 bg-black/80 border border-gray-700 text-xs text-gray-200 p-2 rounded shadow-lg text-left">
                                ${marketProfile.market_size_explanation}
                            </span>
                        </span>` : ''}
                    </div>
                    <div class="text-2xl font-bold text-blue-300">${marketSize}</div>
                    <div class="text-sm text-gray-400 mt-1">Market Size</div>
                </div>
                <div class="bg-black/40 border border-green-400/30 rounded-2xl p-6 text-center">
                    <div class="flex items-center justify-center gap-2 mb-2">
                        <div class="text-3xl">💰</div>
                        ${explainability && explainability.funding_potential_explanation ? `
                        <span class="relative group cursor-help text-gray-400">ⓘ
                            <span class="absolute z-10 hidden group-hover:block -top-1 left-5 w-64 bg-black/80 border border-gray-700 text-xs text-gray-200 p-2 rounded shadow-lg text-left">
                                ${explainability.funding_potential_explanation}
                            </span>
                        </span>` : ''}
                    </div>
                    <div class="text-2xl font-bold text-green-300">${fundingPotential.toFixed(1)}/5</div>
                    <div class="text-sm text-gray-400 mt-1">Funding Potential</div>
                    ${api.formatScoreBar(fundingPotential, 5)}
                </div>
            </div>

            <!-- Team Recommendations -->
            ${teamRecommendations.length > 0 ? `
                <div class="bg-black/40 border border-blue-400/30 rounded-2xl p-6">
                    <h3 class="text-xl font-bold mb-4 flex items-center gap-2">
                        <span>👥</span>
                        <span>Team Recommendations</span>
                    </h3>
                    <ul class="space-y-2">
                        ${teamRecommendations.map(rec => `
                            <li class="flex items-start gap-2 text-gray-300">
                                <span class="text-blue-400 mt-1">•</span>
                                <span>${rec}</span>
                            </li>
                        `).join('')}
                    </ul>
                </div>
            ` : ''}

            <!-- Funding Options -->
            ${fundingOptions.length > 0 ? `
                <div class="bg-black/40 border border-green-400/30 rounded-2xl p-6">
                    <h3 class="text-xl font-bold mb-4 flex items-center gap-2">
                        <span>💰</span>
                        <span>Funding Options</span>
                    </h3>
                    <ul class="space-y-2">
                        ${fundingOptions.map(option => `
                            <li class="flex items-start gap-2 text-gray-300">
                                <span class="text-green-400 mt-1">•</span>
                                <span>${option}</span>
                            </li>
                        `).join('')}
                    </ul>
                </div>
            ` : ''}

            <!-- Legal Requirements -->
            ${legalRequirements.length > 0 ? `
                <div class="bg-black/40 border border-orange-400/30 rounded-2xl p-6">
                    <h3 class="text-xl font-bold mb-4 flex items-center gap-2">
                        <span>⚖️</span>
                        <span>Legal Requirements</span>
                    </h3>
                    <ul class="space-y-2">
                        ${legalRequirements.map(req => `
                            <li class="flex items-start gap-2 text-gray-300">
                                <span class="text-orange-400 mt-1">•</span>
                                <span>${req}</span>
                            </li>
                        `).join('')}
                    </ul>
                </div>
            ` : ''}

            <!-- Suggestions -->
            ${suggestions.length > 0 ? `
                <div class="bg-black/40 border border-yellow-400/30 rounded-2xl p-6">
                    <h3 class="text-xl font-bold mb-4 flex items-center gap-2">
                        <span>💡</span>
                        <span>Recommendations</span>
                    </h3>
                    <ul class="space-y-2">
                        ${suggestions.map(suggestion => `
                            <li class="flex items-start gap-2 text-gray-300">
                                <span class="text-yellow-400 mt-1">•</span>
                                <span>${suggestion}</span>
                            </li>
                        `).join('')}
                    </ul>
                </div>
            ` : ''}

            <!-- Action Buttons -->
            <div class="flex flex-wrap gap-4 justify-center pt-4">
                <a href="/user" class="px-6 py-3 bg-gradient-to-r from-purple-500 to-pink-500 rounded-xl font-bold text-white hover:scale-105 transition-transform">
                    📊 Go to Dashboard
                </a>
                <a href="/roadmap?idea_id=${window.lastRefinedIdeaId || ''}" class="px-6 py-3 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-xl font-bold text-white hover:scale-105 transition-transform">
                    🛤️ Create Roadmap
                </a>
                <button onclick="viewFullReport()" class="px-6 py-3 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-xl font-bold text-white hover:scale-105 transition-transform">
                    📄 View Full Report
                </button>
                <a href="/cofounder" class="px-6 py-3 bg-gradient-to-r from-green-500 to-emerald-500 rounded-xl font-bold text-white hover:scale-105 transition-transform">
                    👥 Find Cofounders
                </a>
                <a href="/intake" class="px-6 py-3 border border-gray-600 rounded-xl font-bold text-gray-300 hover:border-gray-400 transition-colors">
                    ✨ Analyze Another Idea
                </a>
            </div>
        </div>
    `;

    resultsDiv.classList.remove('hidden');

    // Animate results
    gsap.from(resultsDiv.children, {
        y: 20,
        opacity: 0,
        duration: 0.5,
        stagger: 0.1,
        ease: 'power2.out'
    });
}

/**
 * Save idea to database
 */
async function saveIdeaToDatabase(agentResult, formData) {
    try {
        console.log('💾 Starting idea save process...');
        console.log('📊 Full agentResult:', agentResult);
        
        // The agentResult.validation_profile should already be a FullIdeaProfile
        // If not, we need to call /refine-idea to get proper structure
        const validation = agentResult.validation_profile || {};
        
        console.log('🔍 Validation profile:', validation);
        
        // Check if validation_profile has the complete FullIdeaProfile structure
        if (validation.refined_idea && validation.market_profile && validation.overall_confidence_score !== undefined) {
            // Perfect! We have a complete FullIdeaProfile from the agent
            console.log('✅ Using complete FullIdeaProfile from agent');
            
            // FullIdeaProfile has "extra": "forbid" - only send valid fields
            const payload = {
                refined_idea: validation.refined_idea,
                market_profile: validation.market_profile,
                overall_confidence_score: validation.overall_confidence_score,
                explainability: validation.explainability || null,
                concept_card: validation.concept_card || null
            };
            
            console.log('📦 Prepared payload (FullIdeaProfile only):', payload);
            console.log('🔑 Calling createIdea (will extract user_id from JWT)...');
            const savedIdea = await api.createIdea(payload);
            console.log('✅ Idea saved to database with ID:', savedIdea.id);
            console.log('👤 Saved with user_id:', savedIdea.user_id);
            
            window.lastRefinedIdeaId = savedIdea.id;
            console.log('🎯 Stored idea ID for roadmap button:', window.lastRefinedIdeaId);
        } else {
            // Fallback: agent didn't return complete profile, use /refine-idea
            console.log('⚠️ Validation profile incomplete, calling /refine-idea endpoint');
            const fullProfile = await api.refineIdea(formData.rawIdea);
            console.log('✅ Got refined profile from endpoint:', fullProfile);

            // FullIdeaProfile has "extra": "forbid" - only send valid fields
            const payload = {
                refined_idea: fullProfile.refined_idea,
                market_profile: fullProfile.market_profile,
                overall_confidence_score: fullProfile.overall_confidence_score,
                explainability: fullProfile.explainability || null,
                concept_card: fullProfile.concept_card || null
            };
            
            console.log('📦 Prepared payload (FullIdeaProfile only):', payload);
            console.log('🔑 Calling createIdea (will extract user_id from JWT)...');
            const savedIdea = await api.createIdea(payload);
            console.log('✅ Idea saved to database with ID:', savedIdea.id);
            console.log('👤 Saved with user_id:', savedIdea.user_id);
            
            window.lastRefinedIdeaId = savedIdea.id;
            console.log('🎯 Stored idea ID for roadmap button:', window.lastRefinedIdeaId);
        }
    } catch (error) {
        console.error('❌ Failed to save idea:', error);
        console.error('Error details:', error.message, error.stack);
        // Non-critical error - user still sees results
    }
}

/**
 * View full conversation/report
 */
window.viewFullReport = async function() {
    if (!currentConversationId) {
        showError('No conversation ID available');
        return;
    }

    try {
        const history = await api.getConversationHistory(currentConversationId);
        
        // Create modal with full conversation
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 overflow-y-auto';
        modal.innerHTML = `
            <div class="bg-gradient-to-br from-gray-900 to-black border border-purple-400/30 rounded-3xl p-8 max-w-4xl w-full my-8">
                <div class="flex items-center justify-between mb-6">
                    <h2 class="text-2xl font-bold">
                        <span class="holographic-text-pro">Full Analysis Report</span>
                    </h2>
                    <button onclick="this.closest('.fixed').remove()" class="text-gray-400 hover:text-white text-2xl">×</button>
                </div>
                <div class="space-y-4 max-h-96 overflow-y-auto">
                    ${history.messages.map(msg => `
                        <div class="bg-black/40 border border-gray-700 rounded-xl p-4">
                            <div class="text-sm text-gray-400 mb-2">${msg.role === 'user' ? '👤 User' : '🤖 Agent'}</div>
                            <div class="text-gray-300 whitespace-pre-wrap">${msg.content}</div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        gsap.from(modal.querySelector('div'), {
            scale: 0.9,
            opacity: 0,
            duration: 0.3
        });
    } catch (error) {
        showError('Failed to load full report');
    }
};

/**
 * Show error message
 */
function showError(message) {
    const errorDiv = document.getElementById('ideaError');
    if (errorDiv) {
        errorDiv.textContent = `❌ Error: ${message}`;
        errorDiv.classList.remove('hidden');
        errorDiv.classList.add('bg-red-500/20', 'border', 'border-red-400/30', 'rounded-xl', 'p-4', 'text-red-300');
    } else {
        alert(`Error: ${message}`);
    }
}

/**
 * Create intake particles (decorative background)
 */
function createIntakeParticles() {
    const container = document.getElementById('intake-particles');
    if (!container) return;

    for (let i = 0; i < 30; i++) {
        const particle = document.createElement('div');
        particle.className = 'intake-particle';
        particle.style.left = Math.random() * 100 + '%';
        particle.style.top = Math.random() * 100 + '%';
        particle.style.animationDelay = Math.random() * 15 + 's';
        container.appendChild(particle);
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeIntakePage);
} else {
    initializeIntakePage();
}

// ===================================
// EXPLAINABLE AI (XAI) MODAL LOGIC
// ===================================

/**
 * Open the explanation modal with dimension details
 */
function openExplanation(key, title, text, scoreVal = 0.5) {
    console.log('🔍 Opening explanation for:', key, 'Score:', scoreVal);
    
    // Format the Title (e.g., "problem_clarity" -> "Problem Clarity")
    const formattedTitle = title.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    
    // Set Content
    document.getElementById('modal-title').innerText = formattedTitle;
    document.getElementById('modal-text').innerText = text || "No detailed AI insight available for this metric yet. The analysis may still be processing.";
    
    // Set Score Badge
    const scorePct = Math.round(scoreVal * 100);
    const scoreBadge = document.getElementById('insight-score');
    scoreBadge.innerText = `${scorePct}% SCORE`;
    
    // Color code the badge based on score
    if (scorePct > 70) {
        scoreBadge.style.color = '#34d399';
        scoreBadge.style.background = 'rgba(16, 185, 129, 0.1)';
        scoreBadge.style.borderColor = 'rgba(16, 185, 129, 0.3)';
    } else if (scorePct > 40) {
        scoreBadge.style.color = '#facc15';
        scoreBadge.style.background = 'rgba(250, 204, 21, 0.1)';
        scoreBadge.style.borderColor = 'rgba(250, 204, 21, 0.3)';
    } else {
        scoreBadge.style.color = '#f87171';
        scoreBadge.style.background = 'rgba(248, 113, 113, 0.1)';
        scoreBadge.style.borderColor = 'rgba(248, 113, 113, 0.3)';
    }

    // Icon Logic (Pick icon based on dimension name)
    const iconEl = document.getElementById('insight-icon');
    const iconMap = {
        'problem_clarity': 'fas fa-search',
        'problem_significance': 'fas fa-exclamation-triangle',
        'solution_specificity': 'fas fa-cogs',
        'market_validation': 'fas fa-chart-line',
        'technical_complexity': 'fas fa-code',
        'technical_viability': 'fas fa-check-circle',
        'differentiation': 'fas fa-fingerprint',
        'scalability': 'fas fa-rocket'
    };
    iconEl.className = iconMap[key] || 'fas fa-brain';

    // Show Recommendation Box if score is low
    const recBox = document.getElementById('insight-rec-box');
    const recText = document.getElementById('insight-recommendation');
    if (scorePct < 60) {
        recBox.classList.remove('hidden');
        const recommendations = {
            'problem_clarity': 'Define the problem more specifically with concrete examples.',
            'problem_significance': 'Provide data or research showing the scale of the problem.',
            'solution_specificity': 'Add more technical details about how your solution works.',
            'market_validation': 'Conduct user interviews or surveys to validate demand.',
            'technical_complexity': 'Simplify your technical approach or break it into phases.',
            'technical_viability': 'Research existing technologies that can help implement this.',
            'differentiation': 'Clearly explain what makes your solution unique.',
            'scalability': 'Outline how the solution can grow to serve more users.'
        };
        recText.innerText = recommendations[key] || 'Focus on improving this dimension to increase overall feasibility.';
    } else {
        recBox.classList.add('hidden');
    }

    // Show Modal
    const modal = document.getElementById('explanation-modal');
    modal.classList.add('active');
}

/**
 * Close the explanation modal
 */
function closeExplanation() {
    const modal = document.getElementById('explanation-modal');
    modal.classList.remove('active');
}

// Close on Escape Key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        const modal = document.getElementById('explanation-modal');
        if (modal && modal.classList.contains('active')) {
            closeExplanation();
        }
    }
});


// Close modal on Escape key
document.addEventListener('keydown', function(event) {
    if (event.key === "Escape") {
        const modal = document.getElementById('explanation-modal');
        if (modal && !modal.classList.contains('hidden')) {
            closeExplanation();
        }
    }
});

// Make functions globally available
window.openExplanation = openExplanation;
window.closeExplanation = closeExplanation;

// Event delegation for Explain buttons (handles dynamically created content)
document.addEventListener('click', function(event) {
    // Check if clicked element is an explain button or inside analysis card
    const explainBtn = event.target.closest('.explain-btn');
    const analysisCard = event.target.closest('.analysis-card');
    
    if (explainBtn && analysisCard) {
        event.stopPropagation();
        const dimension = analysisCard.getAttribute('data-dimension');
        const title = analysisCard.getAttribute('data-title');
        const explanation = analysisCard.getAttribute('data-explanation');
        const score = parseFloat(analysisCard.getAttribute('data-score')) || 0.5;
        
        console.log('🔘 Explain button clicked!', {dimension, title, explanation, score});
        openExplanation(dimension, title, explanation, score);
    } else if (analysisCard) {
        const dimension = analysisCard.getAttribute('data-dimension');
        const title = analysisCard.getAttribute('data-title');
        const explanation = analysisCard.getAttribute('data-explanation');
        const score = parseFloat(analysisCard.getAttribute('data-score')) || 0.5;
        
        console.log('🔘 Analysis card clicked!', {dimension, title, explanation, score});
        openExplanation(dimension, title, explanation, score);
    }
});
