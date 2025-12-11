/**
 * Elevare API Client
 * Unified JavaScript client for all 37 backend API endpoints
 * Connects beautiful frontend to powerful AI backend
 */

const API_BASE_URL = window.location.origin;
const API_V1 = `${API_BASE_URL}/api/v1`;

class ElevareAPI {
    constructor() {
        this.userId = this.getUserId();
        this.teamId = this.getTeamId();
    }

    /**
     * Helper: Get or create user ID
     */
    getUserId() {
        let userId = localStorage.getItem('elevare_user_id');
        if (!userId) {
            userId = 'user_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('elevare_user_id', userId);
        }
        return userId;
    }

    /**
     * Helper: Get or create team ID
     */
    getTeamId() {
        let teamId = localStorage.getItem('elevare_team_id');
        if (!teamId) {
            teamId = 'team_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('elevare_team_id', teamId);
        }
        return teamId;
    }

    /**
     * Helper: Make API request
     */
    async request(endpoint, options = {}) {
        const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;
        
        // Get JWT token
        const token = localStorage.getItem('access_token');
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        
        const config = {
            headers: headers,
            ...options
        };

        try {
            const response = await fetch(url, config);
            
            if (response.status === 401) {
                // Token expired or invalid
                localStorage.removeItem('access_token');
                localStorage.removeItem('token_type');
                // Only redirect if not already on login/register pages
                if (!window.location.pathname.includes('/login') && !window.location.pathname.includes('/profile-setup')) {
                    window.location.href = '/login';
                }
                throw new Error('Unauthorized');
            }

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `API Error: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error(`API Request Failed: ${endpoint}`, error);
            throw error;
        }
    }

    // ==========================================
    // AUTONOMOUS AGENT API (Phase 3)
    // ==========================================

    /**
     * Invoke the autonomous agent workflow
     * Returns comprehensive startup analysis
     */
    async invokeAgent(rawIdea, options = {}) {
        return this.request(`${API_V1}/agent/invoke`, {
            method: 'POST',
            body: JSON.stringify({
                raw_idea: rawIdea,
                conversation_id: options.conversationId || this.userId,
                team_id: options.teamId || this.teamId,
                stream: false
            })
        });
    }

    /**
     * Get conversation history
     */
    async getConversationHistory(conversationId) {
        return this.request(`${API_V1}/agent/conversations/${conversationId || this.userId}`);
    }

    // ==========================================
    // AI MENTOR API (Phase 4)
    // ==========================================

    /**
     * Ask the AI Mentor a question (RAG-powered)
     */
    async askMentor(question) {
        return this.request(`${API_V1}/mentor/ask`, {
            method: 'POST',
            body: JSON.stringify({ question })
        });
    }

    /**
     * Get mentor status and capabilities
     */
    async getMentorStatus() {
        return this.request(`${API_V1}/mentor/status`);
    }

    /**
     * Get available mentor topics
     */
    async getMentorTopics() {
        return this.request(`${API_V1}/mentor/topics`);
    }

    // ==========================================
    // COLLABORATION API (Phase 4 - WebSocket)
    // ==========================================

    /**
     * Connect to team WebSocket chat
     */
    connectToTeam(teamId, callbacks = {}) {
        const ws = new WebSocket(`ws://${window.location.host}${API_V1}/collaboration/ws/team/${teamId || this.teamId}`);
        
        ws.onopen = () => {
            console.log('✅ Connected to team chat');
            if (callbacks.onOpen) callbacks.onOpen();
        };

        ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                if (callbacks.onMessage) callbacks.onMessage(message);
            } catch (error) {
                console.error('WebSocket message parse error:', error);
            }
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            if (callbacks.onError) callbacks.onError(error);
        };

        ws.onclose = () => {
            console.log('❌ Disconnected from team chat');
            if (callbacks.onClose) callbacks.onClose();
        };

        return ws;
    }

    /**
     * Get list of active teams
     */
    async getActiveTeams() {
        return this.request(`${API_V1}/collaboration/teams`);
    }

    /**
     * Get team status
     */
    async getTeamStatus(teamId) {
        return this.request(`${API_V1}/collaboration/team/${teamId || this.teamId}/status`);
    }

    // ==========================================
    // IDEA VALIDATION API
    // ==========================================

    /**
     * Crystallize an idea into a structured blueprint
     * Returns: IdeaStructure with tech_stack, regulatory_needs, co_founder_roles, search_queries
     */
    async crystallizeIdea(rawIdeaText) {
        return this.request('/idea/crystallize', {
            method: 'POST',
            body: JSON.stringify({ raw_idea_text: rawIdeaText })
        });
    }

    /**
     * Refine and validate an idea (LLM + Market analysis)
     */
    async refineIdea(rawIdeaText) {
        return this.request('/refine-idea', {
            method: 'POST',
            body: JSON.stringify({ raw_idea_text: rawIdeaText })
        });
    }

    /**
     * Get market profile for a concept
     */
    async getMarketProfile(refinedConcept, location = null) {
        const params = new URLSearchParams({ refined_concept: refinedConcept });
        if (location) params.append('location', location);
        return this.request(`/mcp/concept-profile?${params}`);
    }

    // ==========================================
    // IDEAS CRUD API
    // ==========================================

    /**
     * Create a new idea
     */
    async createIdea(ideaData, userId = null) {
        console.log('🔍 createIdea called with userId:', userId);
        
        // Get user ID from JWT token if logged in
        let uid = userId;
        if (!uid) {
            const token = localStorage.getItem('access_token');
            console.log('🔑 JWT token exists:', !!token);
            if (token) {
                try {
                    const payload = JSON.parse(atob(token.split('.')[1]));
                    uid = payload.sub; // Extract user ID from JWT
                    console.log('✅ Extracted user_id from JWT:', uid);
                } catch (e) {
                    console.error('Failed to decode JWT for user ID:', e);
                }
            }
        }
        
        // Fallback to stored profile ID if no JWT
        if (!uid) {
            uid = this.getCurrentProfileId();
            console.log('⚠️ Using fallback profile ID:', uid);
        }
        
        const qs = uid != null ? `?user_id=${encodeURIComponent(uid)}` : '';
        console.log('📤 POST /ideas/ with query string:', qs);
        console.log('📊 Idea data:', ideaData);
        
        const result = await this.request(`/ideas/${qs}`, {
            method: 'POST',
            body: JSON.stringify(ideaData)
        });
        
        console.log('✅ Server response:', result);
        return result;
    }

    /**
     * Get all ideas (optionally filter by user)
     */
    async listIdeas(userId = null) {
        // Get user ID from JWT token if logged in
        let uid = userId;
        if (!uid) {
            const token = localStorage.getItem('access_token');
            if (token) {
                try {
                    const payload = JSON.parse(atob(token.split('.')[1]));
                    uid = payload.sub; // Extract user ID from JWT
                } catch (e) {
                    console.error('Failed to decode JWT for user ID:', e);
                }
            }
        }
        
        const params = uid ? `?user_id=${uid}` : '';
        return this.request(`/ideas/${params}`);
    }

    /**
     * Get a specific idea by ID
     */
    async getIdea(ideaId) {
        return this.request(`/ideas/${ideaId}`);
    }

    /**
     * Update an idea
     */
    async updateIdea(ideaId, ideaData) {
        return this.request(`/ideas/${ideaId}`, {
            method: 'PUT',
            body: JSON.stringify(ideaData)
        });
    }

    /**
     * Delete an idea
     */
    async deleteIdea(ideaId) {
        return this.request(`/ideas/${ideaId}`, {
            method: 'DELETE'
        });
    }

    // ==========================================
    // COFOUNDER MATCHING API
    // ==========================================

    /**
     * Create user profile
     */
    async createUserProfile(profileData) {
        return this.request('/matching/users', {
            method: 'POST',
            body: JSON.stringify(profileData)
        });
    }

    /**
     * Get all users (optionally filter by interest/location)
     */
    async getUsers(filters = {}) {
        const params = new URLSearchParams();
        if (filters.interest) params.append('interest', filters.interest);
        if (filters.location) params.append('location', filters.location);
        
        const queryString = params.toString();
        return this.request(`/matching/users${queryString ? '?' + queryString : ''}`);
    }

    /**
     * Find compatible cofounders for a user
     */
    async findCofounders(userId, domain, requiredSkills = []) {
        // Backend currently exposes /matching/matches/{user_id}?limit=20
        // Domain & requiredSkills are not yet supported server-side; keep for future extension.
        const limit = 20;
        return this.request(`/matching/matches/${userId}?limit=${limit}`);
    }

    /**
     * Find cofounders based on a startup idea (NEW: Real-world matching)
     */
    async findCofoundersByIdea(ideaText, topK = 10, excludeUserId = null) {
        const body = {
            idea_text: ideaText,
            top_k: topK
        };
        
        // Add exclude_user_id if provided
        if (excludeUserId) {
            body.exclude_user_id = excludeUserId;
            console.log('🚨 API CLIENT: Excluding user ID:', excludeUserId);
        } else {
            console.warn('⚠️ API CLIENT: No user ID to exclude!');
        }
        
        console.log('📤 Sending to API:', JSON.stringify(body, null, 2));
        
        return this.request('/matching/find-cofounders', {
            method: 'POST',
            body: JSON.stringify(body)
        });
    }

    // ==========================================
    // HELPER METHODS
    // ==========================================

    /**
     * Persist and retrieve the selected profile (for cross-page context)
     */
    setCurrentProfile(id, name) {
        if (id != null) localStorage.setItem('elevare_profile_id', String(id));
        if (name) localStorage.setItem('elevare_profile_name', name);
    }

    getCurrentProfileId() {
        const v = localStorage.getItem('elevare_profile_id');
        return v ? parseInt(v, 10) : null;
    }

    getCurrentProfileName() {
        return localStorage.getItem('elevare_profile_name') || null;
    }

    async getUserById(id) {
        try {
            const users = await this.getUsers();
            return users.find(u => String(u.id) === String(id)) || null;
        } catch (e) {
            return null;
        }
    }

    /**
     * Display a loading state
     */
    showLoading(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = '<div class="loading-spinner">⏳ Loading...</div>';
        }
    }

    /**
     * Display an error
     */
    showError(elementId, errorMessage) {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = `
                <div class="error-message bg-red-500/20 border border-red-500 rounded-lg p-4">
                    <p class="text-red-200">❌ ${errorMessage}</p>
                </div>
            `;
        }
    }

    /**
     * Display success
     */
    showSuccess(elementId, successMessage) {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = `
                <div class="success-message bg-green-500/20 border border-green-500 rounded-lg p-4">
                    <p class="text-green-200">✅ ${successMessage}</p>
                </div>
            `;
        }
    }

    /**
     * Format a score as a visual bar
     */
    formatScoreBar(score, maxScore = 5) {
        const percentage = (score / maxScore) * 100;
        const color = percentage > 70 ? 'bg-green-500' : percentage > 40 ? 'bg-yellow-500' : 'bg-red-500';
        
        return `
            <div class="score-bar w-full bg-gray-700 rounded-full h-4">
                <div class="${color} h-4 rounded-full" style="width: ${percentage}%"></div>
            </div>
            <p class="text-sm text-gray-400 mt-1">${score.toFixed(1)} / ${maxScore}</p>
        `;
    }

    /**
     * Optional: browser-friendly streaming for the agent via GET SSE
     */
    openAgentStream(rawIdea, { conversationId, teamId } = {}) {
        const params = new URLSearchParams({
            raw_idea: rawIdea,
            conversation_id: conversationId || this.userId,
            team_id: teamId || this.teamId
        });
        const url = `${API_V1}/agent/invoke/stream?${params.toString()}`;
        return new EventSource(url);
    }

    /**
     * Health and MCP utilities
     */
    async getHealth() { return this.request('/healthz'); }
    async getMcpStatus() { return this.request('/mcp/status'); }
}

// Create global API instance
const api = new ElevareAPI();

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ElevareAPI, api };
}
