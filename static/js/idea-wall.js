/**
 * Idea Wall Page Integration
 * Real-time collaborative idea feed with WebSocket support
 */

let websocket = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY = 3000;
let allIdeas = [];
let isConnected = false;

/**
 * Initialize the idea wall page
 */
async function initializeIdeaWall() {
    // Load initial ideas from database
    await loadIdeas();
    
    // Connect to WebSocket for real-time updates
    connectToPublicTeam();
    
    // Setup event listeners
    setupEventListeners();
    
    // Animate page entrance
    animatePageEntrance();
    
    // Update connection status every 5 seconds
    setInterval(updateConnectionStatus, 5000);
}

/**
 * Load ideas from database
 */
async function loadIdeas() {
    try {
        const ideas = await api.listIdeas();
        allIdeas = ideas;
        
        displayIdeas(ideas);
        
        console.log(`✅ Loaded ${ideas.length} ideas from database`);
    } catch (error) {
        console.error('Failed to load ideas:', error);
        showError('Failed to load ideas. Please refresh the page.');
    }
}

/**
 * Connect to WebSocket public team
 */
function connectToPublicTeam() {
    const teamId = 'public'; // Public idea wall team
    
    websocket = api.connectToTeam(teamId, {
        onConnect: handleWebSocketConnect,
        onMessage: handleWebSocketMessage,
        onDisconnect: handleWebSocketDisconnect,
        onError: handleWebSocketError
    });
}

/**
 * Handle WebSocket connection
 */
function handleWebSocketConnect() {
    console.log('✅ Connected to Idea Wall (WebSocket)');
    isConnected = true;
    reconnectAttempts = 0;
    
    updateConnectionBadge(true);
    
    // Show connection notification
    showNotification('🔌 Connected to live idea feed', 'success');
}

/**
 * Handle WebSocket message
 */
function handleWebSocketMessage(message) {
    console.log('📩 WebSocket message:', message);
    
    const data = typeof message === 'string' ? JSON.parse(message) : message;
    
    switch (data.type) {
        case 'system':
            handleSystemMessage(data);
            break;
        case 'user_joined':
            handleUserJoined(data);
            break;
        case 'user_left':
            handleUserLeft(data);
            break;
        case 'new_idea':
            handleNewIdea(data);
            break;
        case 'agent_notification':
            handleAgentNotification(data);
            break;
        case 'idea_update':
            handleIdeaUpdate(data);
            break;
        case 'chat':
            handleChatMessage(data);
            break;
        default:
            console.log('Unknown message type:', data.type);
    }
}

/**
 * Handle WebSocket disconnect
 */
function handleWebSocketDisconnect() {
    console.log('❌ Disconnected from Idea Wall');
    isConnected = false;
    
    updateConnectionBadge(false);
    
    // Attempt reconnection
    if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
        reconnectAttempts++;
        console.log(`🔄 Attempting reconnection (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`);
        
        setTimeout(() => {
            connectToPublicTeam();
        }, RECONNECT_DELAY);
    } else {
        showNotification('⚠️ Lost connection to live feed. Please refresh the page.', 'error');
    }
}

/**
 * Handle WebSocket error
 */
function handleWebSocketError(error) {
    console.error('WebSocket error:', error);
    showNotification('Connection error. Retrying...', 'warning');
}

/**
 * Handle system message
 */
function handleSystemMessage(data) {
    console.log('🔔 System:', data.message);
    showNotification(data.message, 'info');
}

/**
 * Handle user joined
 */
function handleUserJoined(data) {
    const activeUsers = data.active_users || 1;
    updateActiveUsersCount(activeUsers);
    
    showNotification(`👋 Someone joined the idea wall (${activeUsers} active)`, 'info');
}

/**
 * Handle user left
 */
function handleUserLeft(data) {
    const activeUsers = data.active_users || 0;
    updateActiveUsersCount(activeUsers);
}

/**
 * Handle new idea added
 */
function handleNewIdea(data) {
    const idea = data.idea || data;
    
    // Add to local array
    allIdeas.unshift(idea);
    
    // Create and animate new idea card
    const container = document.getElementById('ideas-grid');
    if (container) {
        const card = createIdeaCard(idea);
        container.insertAdjacentHTML('afterbegin', card);
        
        // Animate entrance
        const newCard = container.firstElementChild;
        gsap.from(newCard, {
            scale: 0.8,
            opacity: 0,
            y: -30,
            duration: 0.6,
            ease: 'back.out(1.7)'
        });
        
        // Add pulse effect
        newCard.classList.add('new-idea-pulse');
        setTimeout(() => newCard.classList.remove('new-idea-pulse'), 3000);
    }
    
    showNotification('✨ New idea added to the wall!', 'success');
}

/**
 * Handle agent notification
 */
function handleAgentNotification(data) {
    const message = data.message || data.content || 'Agent completed analysis';
    const ideaId = data.idea_id || data.ideaId;
    
    showNotification(`🤖 ${message}`, 'success');
    
    // If we have the idea on screen, highlight it
    if (ideaId) {
        const ideaCard = document.querySelector(`[data-idea-id="${ideaId}"]`);
        if (ideaCard) {
            ideaCard.classList.add('highlight-pulse');
            setTimeout(() => ideaCard.classList.remove('highlight-pulse'), 2000);
        }
    }
}

/**
 * Handle idea update
 */
function handleIdeaUpdate(data) {
    const ideaId = data.idea_id || data.id;
    const updates = data.updates || data;
    
    // Update local data
    const ideaIndex = allIdeas.findIndex(i => i.id === ideaId);
    if (ideaIndex !== -1) {
        allIdeas[ideaIndex] = { ...allIdeas[ideaIndex], ...updates };
        
        // Re-render that specific card
        const ideaCard = document.querySelector(`[data-idea-id="${ideaId}"]`);
        if (ideaCard) {
            ideaCard.classList.add('updating-pulse');
            setTimeout(() => ideaCard.classList.remove('updating-pulse'), 1000);
        }
    }
}

/**
 * Handle chat message
 */
function handleChatMessage(data) {
    // Could implement a global chat sidebar here
    console.log('💬 Chat:', data.message);
}

/**
 * Display ideas in the grid
 */
function displayIdeas(ideas) {
    const container = document.getElementById('ideas-grid');
    if (!container) return;
    
    if (ideas.length === 0) {
        container.innerHTML = `
            <div class="col-span-full text-center py-16">
                <div class="text-6xl mb-4">💡</div>
                <h3 class="text-2xl font-bold text-gray-300 mb-2">No Ideas Yet</h3>
                <p class="text-gray-400 mb-6">Be the first to share your innovative idea!</p>
                <a href="/intake" class="cta-button inline-block text-white font-bold py-3 px-6 rounded-lg">
                    Submit Your Idea
                </a>
            </div>
        `;
        return;
    }
    
    container.innerHTML = ideas.map(idea => createIdeaCard(idea)).join('');
    
    // Animate cards on load
    gsap.from('#ideas-grid > *', {
        y: 30,
        opacity: 0,
        duration: 0.6,
        stagger: 0.1,
        ease: 'power2.out'
    });
}

/**
 * Create idea card HTML
 */
function createIdeaCard(idea) {
    // Support new IdeaRecord format from /ideas API (refined_idea nested)
    const refined = idea.refined_idea || {};
    const domain = refined.core_domain || idea.core_domain || idea.domain || 'General';
    const score = refined.initial_feasibility_score || idea.initial_feasibility_score || idea.feasibility_score || 0;
    const problem = refined.problem_statement || idea.problem_statement || 'No description available';
    
    // Determine color scheme based on domain
    const colorSchemes = {
        'EdTech': { border: 'violet-400', bg: 'violet-600', button: 'violet' },
        'FinTech': { border: 'pink-400', bg: 'pink-600', button: 'pink' },
        'HealthTech': { border: 'sky-400', bg: 'sky-600', button: 'sky' },
        'AgriTech': { border: 'green-400', bg: 'green-600', button: 'green' },
        'AI/ML': { border: 'purple-400', bg: 'purple-600', button: 'purple' },
        'SaaS': { border: 'blue-400', bg: 'blue-600', button: 'blue' },
        'E-commerce': { border: 'orange-400', bg: 'orange-600', button: 'orange' }
    };
    
    const colors = colorSchemes[domain] || { border: 'gray-400', bg: 'gray-600', button: 'gray' };
    
    return `
        <div class="glass-morphism rounded-xl p-6 text-left hover:border-${colors.border} transition duration-300 idea-card" 
             data-idea-id="${idea.id || ''}">
            <div class="flex items-start justify-between mb-3">
                <div class="flex-1">
                    <h5 class="font-bold text-lg mb-2">${refined.idea_title?.substring(0, 60) || 'Untitled Idea'}${refined.idea_title ? '' : ''}</h5>
                    ${score > 0 ? `
                        <div class="flex items-center gap-2 mb-2">
                            <span class="text-xs text-gray-400">Feasibility:</span>
                            <div class="flex gap-1">
                                ${Array.from({length: 5}, (_, i) => `
                                    <i class="fas fa-star text-xs ${i < score ? 'text-yellow-400' : 'text-gray-600'}"></i>
                                `).join('')}
                            </div>
                            <span class="text-xs text-gray-300">${score.toFixed(1)}/5</span>
                        </div>
                    ` : ''}
                </div>
                <div class="ml-4">
                    <div class="w-12 h-12 rounded-full bg-gradient-to-br from-${colors.bg}/20 to-${colors.bg}/40 border border-${colors.border} flex items-center justify-center text-2xl">
                        ${getDomainEmoji(domain)}
                    </div>
                </div>
            </div>
            
            <p class="text-sm text-gray-300 mb-4 line-clamp-3">${problem}</p>
            
            <div class="flex items-center justify-between text-xs text-gray-400">
                <span><i class="fas fa-tags mr-1"></i> ${domain}</span>
                <button onclick="viewIdeaDetails('${idea.id}')" 
                        class="bg-${colors.button}-600/50 text-white px-3 py-1 rounded-md hover:bg-${colors.button}-600 transition">
                    View Details
                </button>
            </div>
            
            ${(idea.conversation_id || idea.refined_conversation_id) ? `
                <div class="mt-3 pt-3 border-t border-gray-700">
                    <button onclick="viewAgentAnalysis('${idea.conversation_id || idea.refined_conversation_id}')" 
                            class="text-xs text-purple-400 hover:text-purple-300 transition">
                        <i class="fas fa-robot mr-1"></i> View AI Analysis
                    </button>
                </div>
            ` : ''}
        </div>
    `;
}

/**
 * Get emoji for domain
 */
function getDomainEmoji(domain) {
    const emojis = {
        'EdTech': '🎓',
        'FinTech': '💰',
        'HealthTech': '🏥',
        'AgriTech': '🌱',
        'AI/ML': '🤖',
        'SaaS': '☁️',
        'E-commerce': '🛒',
        'Other': '💡'
    };
    return emojis[domain] || '💡';
}

/**
 * View idea details
 */
window.viewIdeaDetails = function(ideaId) {
    const idea = allIdeas.find(i => i.id === ideaId);
    if (!idea) {
        showError('Idea not found');
        return;
    }
    
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 overflow-y-auto';
    modal.innerHTML = `
        <div class="bg-gradient-to-br from-gray-900 to-black border border-purple-400/30 rounded-3xl p-8 max-w-3xl w-full my-8">
            <div class="flex items-center justify-between mb-6">
                <h2 class="text-3xl font-bold">
                    <span class="holographic-text-pro">Idea Details</span>
                </h2>
                <button onclick="this.closest('.fixed').remove()" class="text-gray-400 hover:text-white text-3xl">×</button>
            </div>
            
            <div class="space-y-6">
                <div>
                    <h3 class="text-lg font-bold text-purple-300 mb-2">Full Description</h3>
                    <p class="text-gray-300 bg-black/40 p-4 rounded-lg">${idea.raw_idea_text || 'No description'}</p>
                </div>
                
                ${idea.problem_statement ? `
                    <div>
                        <h3 class="text-lg font-bold text-purple-300 mb-2">Problem Statement</h3>
                        <p class="text-gray-300 bg-black/40 p-4 rounded-lg">${idea.problem_statement}</p>
                    </div>
                ` : ''}
                
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <h3 class="text-sm font-bold text-purple-300 mb-2">Domain</h3>
                        <p class="text-gray-300">${idea.core_domain || 'General'}</p>
                    </div>
                    ${idea.initial_feasibility_score ? `
                        <div>
                            <h3 class="text-sm font-bold text-purple-300 mb-2">Feasibility Score</h3>
                            <p class="text-gray-300">${idea.initial_feasibility_score.toFixed(1)}/5</p>
                        </div>
                    ` : ''}
                </div>
                
                <div class="flex gap-4 pt-4">
                    ${idea.conversation_id ? `
                        <button onclick="viewAgentAnalysis('${idea.conversation_id}')" 
                                class="flex-1 px-6 py-3 bg-gradient-to-r from-purple-500 to-pink-500 rounded-xl font-bold text-white hover:scale-105 transition-transform">
                            <i class="fas fa-robot mr-2"></i>View AI Analysis
                        </button>
                    ` : `
                        <button onclick="analyzeThisIdea('${idea.id}')" 
                                class="flex-1 px-6 py-3 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-xl font-bold text-white hover:scale-105 transition-transform">
                            <i class="fas fa-magic mr-2"></i>Analyze with AI
                        </button>
                    `}
                    <button onclick="this.closest('.fixed').remove()" 
                            class="px-6 py-3 border border-gray-600 rounded-xl font-bold text-gray-300 hover:border-gray-400 transition-colors">
                        Close
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    gsap.from(modal.querySelector('div'), {
        scale: 0.9,
        opacity: 0,
        duration: 0.3
    });
};

/**
 * View agent analysis
 */
window.viewAgentAnalysis = async function(conversationId) {
    try {
        const history = await api.getConversationHistory(conversationId);
        
        // Find the final report message
        const finalReport = history.messages?.findLast(msg => 
            msg.role === 'assistant' && msg.content.includes('feasibility')
        );
        
        if (!finalReport) {
            showError('Analysis not found');
            return;
        }
        
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 overflow-y-auto';
        modal.innerHTML = `
            <div class="bg-gradient-to-br from-gray-900 to-black border border-purple-400/30 rounded-3xl p-8 max-w-4xl w-full my-8">
                <div class="flex items-center justify-between mb-6">
                    <h2 class="text-2xl font-bold">
                        <span class="holographic-text-pro">AI Analysis Report</span>
                    </h2>
                    <button onclick="this.closest('.fixed').remove()" class="text-gray-400 hover:text-white text-3xl">×</button>
                </div>
                <div class="bg-black/40 border border-gray-700 rounded-xl p-6 max-h-96 overflow-y-auto">
                    <div class="text-gray-300 whitespace-pre-wrap">${finalReport.content}</div>
                </div>
                <button onclick="this.closest('.fixed').remove()" 
                        class="mt-6 w-full px-6 py-3 border border-gray-600 rounded-xl font-bold text-gray-300 hover:border-gray-400 transition-colors">
                    Close
                </button>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        gsap.from(modal.querySelector('div'), {
            scale: 0.9,
            opacity: 0,
            duration: 0.3
        });
    } catch (error) {
        console.error('Failed to load analysis:', error);
        showError('Failed to load analysis');
    }
};

/**
 * Analyze idea (redirect to intake)
 */
window.analyzeThisIdea = function(ideaId) {
    // In a full implementation, could pre-populate intake form
    window.location.href = '/intake';
};

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Add event listener for "Submit Your Idea" button if needed
    // Currently handled by HTML href
}

/**
 * Update connection badge
 */
function updateConnectionBadge(connected) {
    let badge = document.getElementById('connection-badge');
    
    if (!badge) {
        // Create badge if it doesn't exist
        const header = document.querySelector('header nav');
        if (header) {
            badge = document.createElement('div');
            badge.id = 'connection-badge';
            badge.className = 'fixed top-20 right-4 z-40';
            header.appendChild(badge);
        }
    }
    
    if (badge) {
        if (connected) {
            badge.innerHTML = `
                <div class="bg-green-500/20 border border-green-400/30 rounded-full px-4 py-2 flex items-center gap-2">
                    <div class="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                    <span class="text-xs font-medium text-green-300">Live</span>
                </div>
            `;
        } else {
            badge.innerHTML = `
                <div class="bg-red-500/20 border border-red-400/30 rounded-full px-4 py-2 flex items-center gap-2">
                    <div class="w-2 h-2 bg-red-400 rounded-full"></div>
                    <span class="text-xs font-medium text-red-300">Offline</span>
                </div>
            `;
        }
    }
}

/**
 * Update active users count
 */
function updateActiveUsersCount(count) {
    const countElement = document.getElementById('active-users-count');
    if (countElement) {
        countElement.textContent = count;
    }
}

/**
 * Update connection status
 */
function updateConnectionStatus() {
    if (websocket && websocket.readyState === WebSocket.OPEN) {
        if (!isConnected) {
            isConnected = true;
            updateConnectionBadge(true);
        }
    } else {
        if (isConnected) {
            isConnected = false;
            updateConnectionBadge(false);
        }
    }
}

/**
 * Show notification
 */
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `fixed top-24 right-4 z-50 max-w-sm`;
    
    const bgColors = {
        success: 'bg-green-500/20 border-green-400/30',
        error: 'bg-red-500/20 border-red-400/30',
        warning: 'bg-yellow-500/20 border-yellow-400/30',
        info: 'bg-blue-500/20 border-blue-400/30'
    };
    
    notification.innerHTML = `
        <div class="${bgColors[type] || bgColors.info} border rounded-xl p-4 backdrop-blur-xl">
            <p class="text-sm text-white">${message}</p>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Animate in
    gsap.from(notification, {
        x: 100,
        opacity: 0,
        duration: 0.3
    });
    
    // Remove after 4 seconds
    setTimeout(() => {
        gsap.to(notification, {
            x: 100,
            opacity: 0,
            duration: 0.3,
            onComplete: () => notification.remove()
        });
    }, 4000);
}

/**
 * Show error
 */
function showError(message) {
    showNotification(`❌ ${message}`, 'error');
}

/**
 * Animate page entrance
 */
function animatePageEntrance() {
    gsap.from('main section', {
        y: 30,
        opacity: 0,
        duration: 0.7,
        ease: 'power2.out'
    });
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeIdeaWall);
} else {
    initializeIdeaWall();
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (websocket) {
        websocket.close();
    }
});
