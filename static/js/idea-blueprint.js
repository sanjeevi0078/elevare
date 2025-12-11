/**
 * IdeaBlueprint Component
 * Visualizes the structural blueprint of an idea after crystallization.
 * This component shows Tech Stack, Compliance Layer, and Critical Roles.
 */

class IdeaBlueprint {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.structure = null;
    }

    /**
     * Render the blueprint visualization
     * @param {Object} structure - The IdeaStructure from /idea/crystallize endpoint
     */
    render(structure) {
        if (!this.container || !structure) {
            console.warn('IdeaBlueprint: No container or structure provided');
            return;
        }

        this.structure = structure;
        
        const html = `
            <div class="idea-blueprint mb-8 animate-fade-in">
                
                <!-- Header: The Refined Identity -->
                <div class="flex items-center justify-between mb-6">
                    <div>
                        <h2 class="text-2xl font-bold bg-gradient-to-r from-purple-400 to-pink-300 bg-clip-text text-transparent">
                            ${this._escapeHtml(structure.refined_title)}
                        </h2>
                        <div class="flex gap-2 mt-2">
                            <span class="bg-purple-500/10 text-purple-300 text-xs px-3 py-1 rounded-full border border-purple-500/20">
                                <i class="fas fa-industry mr-1"></i>${this._escapeHtml(structure.core_domain)}
                            </span>
                            <span class="bg-blue-500/10 text-blue-300 text-xs px-3 py-1 rounded-full border border-blue-500/20">
                                <i class="fas fa-bullseye mr-1"></i>${this._escapeHtml(structure.target_vertical)}
                            </span>
                        </div>
                    </div>
                    <div class="text-right">
                        <span class="text-xs text-gray-500 uppercase tracking-widest">Structural Blueprint</span>
                    </div>
                </div>

                <!-- The Structural Grid -->
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    
                    <!-- Tech Stack Structure -->
                    <div class="blueprint-card bg-[#1a0b2e] border border-white/5 p-4 rounded-xl hover:border-purple-500/30 transition-all duration-300">
                        <div class="flex items-center gap-2 text-gray-400 mb-3 text-xs uppercase tracking-widest font-bold">
                            <i class="fas fa-microchip"></i> Technical Core
                        </div>
                        <div class="flex flex-wrap gap-2">
                            ${structure.tech_stack.map(tech => `
                                <span class="text-xs bg-white/5 text-gray-300 px-2 py-1 rounded font-mono border border-white/10 hover:border-purple-400/50 transition-colors">
                                    ${this._escapeHtml(tech)}
                                </span>
                            `).join('')}
                        </div>
                        <div class="mt-3 pt-3 border-t border-white/5">
                            <div class="text-xs text-gray-500">
                                <i class="fab fa-github mr-1"></i> 
                                <code class="text-purple-400">${this._escapeHtml(structure.search_queries?.github || 'N/A')}</code>
                            </div>
                        </div>
                    </div>

                    <!-- Regulatory/Compliance Structure -->
                    <div class="blueprint-card bg-[#1a0b2e] border border-white/5 p-4 rounded-xl hover:border-yellow-500/30 transition-all duration-300">
                        <div class="flex items-center gap-2 text-gray-400 mb-3 text-xs uppercase tracking-widest font-bold">
                            <i class="fas fa-shield-alt"></i> Compliance Layer
                        </div>
                        ${structure.regulatory_needs && structure.regulatory_needs.length > 0 ? `
                            <ul class="space-y-2">
                                ${structure.regulatory_needs.map(req => `
                                    <li class="text-xs text-yellow-400/80 flex items-center gap-2">
                                        <span class="w-1.5 h-1.5 bg-yellow-500 rounded-full flex-shrink-0"></span> 
                                        ${this._escapeHtml(req)}
                                    </li>
                                `).join('')}
                            </ul>
                        ` : `
                            <p class="text-xs text-gray-500 italic">
                                <i class="fas fa-check-circle text-green-500 mr-1"></i>
                                No specific compliance requirements identified
                            </p>
                        `}
                        <div class="mt-3 pt-3 border-t border-white/5">
                            <div class="text-xs text-gray-500">
                                <i class="fas fa-calendar mr-1"></i> 
                                <code class="text-yellow-400">${this._escapeHtml(structure.search_queries?.events || 'N/A')}</code>
                            </div>
                        </div>
                    </div>

                    <!-- Talent Gaps / Critical Roles Structure -->
                    <div class="blueprint-card bg-[#1a0b2e] border border-white/5 p-4 rounded-xl hover:border-pink-500/30 transition-all duration-300">
                        <div class="flex items-center gap-2 text-gray-400 mb-3 text-xs uppercase tracking-widest font-bold">
                            <i class="fas fa-crosshairs"></i> Critical Roles
                        </div>
                        <div class="space-y-2">
                            ${structure.co_founder_roles.map((role, index) => `
                                <div class="text-xs text-purple-300 bg-purple-500/10 px-3 py-2 rounded border-l-2 border-purple-500 flex items-center gap-2">
                                    <span class="w-5 h-5 rounded-full bg-purple-500/20 flex items-center justify-center text-purple-400 font-bold">${index + 1}</span>
                                    ${this._escapeHtml(role)}
                                </div>
                            `).join('')}
                        </div>
                    </div>

                </div>

                <!-- Action Bar -->
                <div class="mt-6 flex items-center justify-between text-xs text-gray-500">
                    <div class="flex items-center gap-4">
                        <span><i class="fas fa-bolt text-purple-400 mr-1"></i> AI-Crystallized Structure</span>
                        <span><i class="fas fa-code-branch text-blue-400 mr-1"></i> Ready for intelligent matching</span>
                    </div>
                    <button onclick="window.ideaBlueprint?.copySearchQueries()" class="text-gray-400 hover:text-purple-400 transition-colors">
                        <i class="fas fa-copy mr-1"></i> Copy Search Queries
                    </button>
                </div>
            </div>
        `;

        this.container.innerHTML = html;
        
        // Add animation class after render
        requestAnimationFrame(() => {
            this.container.querySelector('.idea-blueprint')?.classList.add('animate-in');
        });
    }

    /**
     * Copy search queries to clipboard
     */
    copySearchQueries() {
        if (!this.structure?.search_queries) return;
        
        const queries = `GitHub: ${this.structure.search_queries.github}\nEvents: ${this.structure.search_queries.events}`;
        navigator.clipboard.writeText(queries).then(() => {
            this._showToast('Search queries copied to clipboard!');
        }).catch(err => {
            console.error('Failed to copy:', err);
        });
    }

    /**
     * Get the search queries for use by other components
     */
    getSearchQueries() {
        return this.structure?.search_queries || null;
    }

    /**
     * Show a toast notification
     */
    _showToast(message) {
        const toast = document.createElement('div');
        toast.className = 'fixed bottom-4 right-4 bg-purple-600 text-white px-4 py-2 rounded-lg shadow-lg animate-fade-in z-50';
        toast.textContent = message;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('animate-fade-out');
            setTimeout(() => toast.remove(), 300);
        }, 2000);
    }

    /**
     * Escape HTML to prevent XSS
     */
    _escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Show loading state
     */
    showLoading() {
        if (!this.container) return;
        
        this.container.innerHTML = `
            <div class="idea-blueprint mb-8 animate-pulse">
                <div class="flex items-center justify-between mb-6">
                    <div>
                        <div class="h-8 bg-gray-700/50 rounded w-64 mb-2"></div>
                        <div class="flex gap-2">
                            <div class="h-6 bg-purple-500/20 rounded-full w-24"></div>
                            <div class="h-6 bg-blue-500/20 rounded-full w-32"></div>
                        </div>
                    </div>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div class="bg-[#1a0b2e] border border-white/5 p-4 rounded-xl h-32"></div>
                    <div class="bg-[#1a0b2e] border border-white/5 p-4 rounded-xl h-32"></div>
                    <div class="bg-[#1a0b2e] border border-white/5 p-4 rounded-xl h-32"></div>
                </div>
            </div>
        `;
    }

    /**
     * Show error state
     */
    showError(message) {
        if (!this.container) return;
        
        this.container.innerHTML = `
            <div class="idea-blueprint mb-8 p-6 bg-red-500/10 border border-red-500/30 rounded-xl">
                <div class="flex items-center gap-3 text-red-400">
                    <i class="fas fa-exclamation-triangle text-2xl"></i>
                    <div>
                        <h3 class="font-bold">Failed to crystallize idea</h3>
                        <p class="text-sm text-red-400/70">${this._escapeHtml(message)}</p>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Clear the blueprint display
     */
    clear() {
        if (this.container) {
            this.container.innerHTML = '';
        }
        this.structure = null;
    }
}

// API function to crystallize an idea
async function crystallizeIdea(rawIdeaText) {
    // Use the global API client if available, otherwise make direct request
    if (window.api && typeof window.api.crystallizeIdea === 'function') {
        return window.api.crystallizeIdea(rawIdeaText);
    }
    
    // Fallback to direct fetch
    try {
        const response = await fetch('/idea/crystallize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`
            },
            body: JSON.stringify({ raw_idea_text: rawIdeaText })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to crystallize idea');
        }

        return await response.json();
    } catch (error) {
        console.error('Crystallize error:', error);
        throw error;
    }
}

// Export for global use
window.IdeaBlueprint = IdeaBlueprint;
window.crystallizeIdea = crystallizeIdea;

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    .animate-fade-in {
        animation: fadeIn 0.5s ease-out forwards;
    }
    
    .animate-fade-out {
        animation: fadeOut 0.3s ease-out forwards;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes fadeOut {
        from { opacity: 1; }
        to { opacity: 0; }
    }
    
    .blueprint-card {
        transition: all 0.3s ease;
    }
    
    .blueprint-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 40px rgba(139, 92, 246, 0.1);
    }
`;
document.head.appendChild(style);
