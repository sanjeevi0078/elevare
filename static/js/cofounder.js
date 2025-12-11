/**
 * Cofounder Matching Page Integration
 * Connects cofounder search UI to Elevare's matching API
 */

let currentMatches = [];
let allUsers = [];
let currentUserId = null;
let userIdeas = [];  // Store user's ideas
let selectedIdeaId = null;  // Currently selected idea

// =============================================================
// HYBRID PROFILE LOADER (GitHub + Synthetic)
// =============================================================
async function loadHybridProfiles(ideaText, topK = 9) {
    try {
        // Remove any static/dummy sample cards before loading real profiles
        hideStaticSamples();
        const resp = await fetch('/matching/hybrid-profiles', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ idea_text: ideaText, top_k: topK })
        });
        if (!resp.ok) throw new Error('Hybrid profile fetch failed');
        const data = await resp.json();
        const profiles = data.profiles || [];
        // Transform envelope -> legacy match structure expected by displayMatches
        const transformed = profiles.map(p => ({
            user: {
                id: p.name + '_' + Math.random().toString(36).slice(2,8), // synthetic lacks id; generate ephemeral
                name: p.name,
                username: null,
                location: p.location,
                interest: '',
                bio: p.bio,
                personality: p.bio,
                commitment_level: p.match_score / 100,
                skills: (p.skills || []).map(s => ({ name: s })),
                avatar_url: p.image,
                profile_url: p.github_url,
                source: p.source === 'ai' ? 'synthetic' : p.source,
                role_type: p.role
            },
            score: p.match_score,
            synergy_analysis: p.match_reason,
            missing_skills_filled: [],
            recommended_action: p.must_connect ? 'Must Connect' : 'Explore',
            intro_message: `Hi ${p.name.split(' ')[0]}, exploring an idea around "${ideaText.split(' ').slice(0,6).join(' ')}" — your ${p.role.toLowerCase()} background looks highly complementary.`
        }));
        currentMatches = transformed;
        displayMatches(transformed);
        updateStatsWithMatches(transformed);
        return transformed;
    } catch (e) {
        console.error('Hybrid profile load error:', e);
        showError('Failed to load hybrid profiles');
        return [];
    }
}

/**
 * Load user's refined ideas
 */
async function loadUserIdeas() {
    try {
        const token = localStorage.getItem('access_token');
        if (!token) {
            console.error('No access token found');
            window.location.href = '/login';
            return;
        }

        // Extract user ID from JWT
        const payload = JSON.parse(atob(token.split('.')[1]));
        currentUserId = payload.sub;
        
        console.log('🔍 Loading ideas for user:', currentUserId);

        // Fetch user's ideas
        const response = await fetch(`/ideas/?user_id=${currentUserId}`);
        if (!response.ok) {
            console.error('Failed to load ideas:', response.status);
            throw new Error('Failed to load ideas');
        }
        
        userIdeas = await response.json();
        console.log('✅ Loaded ideas:', userIdeas.length, userIdeas);

        // Populate selector
        const selector = document.getElementById('idea-selector');
        if (selector) {
            selector.disabled = false; // Enable dropdown
            
            if (userIdeas.length === 0) {
                selector.innerHTML = '<option value="">No ideas yet - create one first!</option>';
                return;
            }

            selector.innerHTML = '<option value="">Choose an idea to find cofounders...</option>' +
                userIdeas.map(idea => {
                    const refined = idea.refined_idea || {};
                    const title = refined.idea_title || 'Untitled Idea';
                    console.log('Adding idea to selector:', idea.id, title);
                    return `<option value="${idea.id}">${title}</option>`;
                }).join('');
            
            // Auto-load first idea if coming from query param
            const urlParams = new URLSearchParams(window.location.search);
            const ideaId = urlParams.get('idea_id');
            if (ideaId) {
                selector.value = ideaId;
                await handleIdeaSelection(parseInt(ideaId));
            }
        }

    } catch (error) {
        console.error('Error loading ideas:', error);
        if (window.api && window.api.showError) {
            window.api.showError('Failed to load your ideas');
        }
    }
}

/**
 * Handle idea selection from dropdown
 */
async function handleIdeaSelection(ideaId) {
    if (!ideaId) return;
    
    selectedIdeaId = ideaId;
    const idea = userIdeas.find(i => i.id === ideaId);
    
    if (!idea) {
        console.error('Idea not found:', ideaId);
        return;
    }
    
    console.log('📋 Selected idea:', idea);
    
    // Extract idea details
    const refined = idea.refined_idea || {};
    const ideaTitle = refined.idea_title || 'Untitled Idea';
    const problemStatement = refined.problem_statement || '';
    const solutionConcept = refined.solution_concept || '';
    
    // Build full idea text for matching
    const ideaText = `${ideaTitle}\n\nProblem: ${problemStatement}\n\nSolution: ${solutionConcept}`;
    
    console.log('🎯 Using idea for matching:', ideaText.substring(0, 100) + '...');
    
    // Update status message
    const statusText = document.getElementById('cf-status-text');
    if (statusText) {
        statusText.textContent = `Ready to find cofounders for: "${ideaTitle}". Click "Start Matching" below!`;
    }
    
    // Store in session for manual matching
    sessionStorage.setItem('matchingIdea', ideaText);
    sessionStorage.setItem('matchingIdeaTitle', ideaTitle);
}

/**
 * Initialize the cofounder page
 */
async function initializeCofounderPage() {
    // Create particles
    createCofounderParticles();
    
    // Load user's refined ideas first
    await loadUserIdeas();
    
    // Load all users for dropdown
    await loadUsers();
    
    // Setup event listeners
    setupEventListeners();
    
    // Animate page entrance
    animatePageEntrance();
    
    // Update stats with real data
    updateStats();
    setupCreateProfileForm();

    // Auto-load current user from JWT
    await loadCurrentUserHeader();
    
    // Initialize selected profile summary from stored selection
    const storedId = api.getCurrentProfileId();
    if (storedId) {
        const user = (allUsers || []).find(u => u.id === storedId);
        if (user) updateSelectedProfileSummary(user);
    }
    
    // Check if we should auto-trigger matching based on an idea
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('autoMatch') === 'true') {
        const ideaText = sessionStorage.getItem('matchingIdea');
        const ideaTitle = sessionStorage.getItem('matchingIdeaTitle');
        
        console.log('🔍 AutoMatch detected. Idea text:', ideaText ? ideaText.substring(0, 50) + '...' : 'NONE');
        console.log('🔍 Idea title:', ideaTitle || 'NONE');
        console.log('🔍 Container exists:', !!document.getElementById('cf-matches-dynamic'));
        
        if (ideaText && ideaText.length >= 20) {
            console.log('✅ Auto-triggering cofounder matching for idea:', ideaTitle);
            
            // Clear the session storage
            sessionStorage.removeItem('matchingIdea');
            sessionStorage.removeItem('matchingIdeaTitle');
            
            // Trigger the search
            try {
                await window.findCofoundersByIdea(ideaText);
                console.log('✅ Matching completed successfully');
            } catch (error) {
                console.error('❌ Error during auto-matching:', error);
            }
        } else {
            console.warn('⚠️ AutoMatch=true but idea text is missing or too short');
        }
    } else {
        // Don't auto-match immediately - wait for user to click "Start Matching" button
        console.log('ℹ️ Waiting for user to click "Start Matching" button or select an idea');
    }
}

/**
 * Manual start matching - called when user clicks "Start Matching" button
 */
window.manualStartMatching = async function() {
    const startBtn = document.getElementById('cf-start-matching-btn');
    const statusText = document.getElementById('cf-status-text');
    
    if (startBtn) {
        startBtn.disabled = true;
        startBtn.innerHTML = '<span>⏳</span><span>Finding matches...</span>';
    }
    
    if (statusText) {
        statusText.textContent = 'Searching for compatible cofounders based on your profile and idea...';
    }
    
    try {
        await autoMatchWithLatestIdea();
        
        // Hide the start button after matching starts
        if (startBtn) {
            startBtn.style.display = 'none';
        }
        
        if (statusText) {
            statusText.textContent = 'Matches found! Scroll down to see your compatible cofounders.';
        }
    } catch (error) {
        console.error('Error starting matching:', error);
        if (startBtn) {
            startBtn.disabled = false;
            startBtn.innerHTML = '<span>🚀</span><span>Start Matching</span>';
        }
        if (statusText) {
            statusText.textContent = 'Error starting matching. Please try again.';
        }
    }
};

/**
 * Auto-load and match with user's latest refined idea
 */
async function autoMatchWithLatestIdea() {
    try {
        // Extract user ID from JWT
        const token = localStorage.getItem('access_token'); // FIXED: was jwt_token
        if (!token) {
            console.log('ℹ️ No access token - user not logged in');
            return;
        }
        
        const payload = JSON.parse(atob(token.split('.')[1]));
        const userId = payload.sub;
        
        console.log('🔍 Auto-matching for user:', userId);
        
        // Fetch user's ideas
        const response = await fetch(`/ideas/?user_id=${userId}`);
        if (!response.ok) {
            console.error('Failed to load ideas:', response.status);
            return;
        }
        
        const ideas = await response.json();
        console.log('📋 User ideas:', ideas.length);
        
        if (ideas && ideas.length > 0) {
            // Get the latest idea (most recent)
            const latestIdea = ideas[0];
            const ideaText = latestIdea.refined_idea.problem_statement + ' ' + 
                           latestIdea.refined_idea.solution;
            const ideaTitle = latestIdea.refined_idea.idea_title;
            
            console.log(`🚀 Auto-matching with latest idea: "${ideaTitle}"`);
            
            // Hide profile selector section completely
            const profileSection = document.querySelector('.glass-morphism-enhanced');
            if (profileSection && profileSection.textContent.includes('Select Your Profile')) {
                profileSection.style.display = 'none';
            }
            
            // Update instructions
            const instructionsEl = document.getElementById('cf-instructions');
            if (instructionsEl) {
                instructionsEl.innerHTML = `
                    <div class="bg-gradient-to-r from-indigo-500/20 to-purple-500/20 border border-indigo-500/30 rounded-lg p-4 mb-6">
                        <h3 class="text-lg font-semibold text-white mb-2">🤖 AI Headhunter Active</h3>
                        <p class="text-gray-300">Finding perfect cofounders for: <strong class="text-indigo-400">${ideaTitle}</strong></p>
                    </div>
                `;
            }
            
            // Trigger AI matching IMMEDIATELY (excluding current user)
            console.log('🚨 EXCLUDING USER ID:', userId, 'Type:', typeof userId);
            await window.findCofoundersByIdea(ideaText, 10, parseInt(userId));
            
        } else {
            // Show message to create an idea first
            const instructionsEl = document.getElementById('cf-instructions');
            if (instructionsEl) {
                instructionsEl.innerHTML = `
                    <div class="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4 mb-6 text-center">
                        <h3 class="text-2xl font-semibold text-yellow-400 mb-3">💡 No Ideas Found</h3>
                        <p class="text-gray-300 mb-4">Create and refine your startup idea first to find perfect cofounders!</p>
                        <a href="/intake" class="inline-block px-6 py-3 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-lg text-white font-bold hover:scale-105 transition-transform">
                            <i class="fas fa-lightbulb mr-2"></i>Create Your Idea
                        </a>
                    </div>
                `;
            }
            
            // Hide matches container
            const matchesEl = document.getElementById('cf-matches-dynamic');
            if (matchesEl) matchesEl.innerHTML = '';
        }
    } catch (error) {
        console.error('Error in auto-match:', error);
    }
}

/**
 * Load all users from database
 */
async function loadUsers() {
    try {
        const users = await api.getUsers();
        allUsers = users;
        
        // Populate user selector dropdown
        const userSelect = document.getElementById('cf-user-select');
        if (userSelect) {
            userSelect.innerHTML = '<option value="">Select Your Profile...</option>';
            users.forEach(user => {
                const option = document.createElement('option');
                option.value = user.id;
                option.textContent = `${user.name} (${user.interest || 'No domain'})`;
                userSelect.appendChild(option);
            });
        }
        
        console.log(`✅ Loaded ${users.length} users`);
    } catch (error) {
        console.error('Failed to load users:', error);
        showError('Failed to load users. Please refresh or check network.');
    }
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Find matches button
    const findBtn = document.getElementById('cf-find-btn');
    if (findBtn) {
        findBtn.addEventListener('click', handleFindMatches);
    }
    
    // Filter tabs
    const filterTabs = document.querySelectorAll('.match-tab');
    filterTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            filterTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            const filter = tab.dataset.filter;
            filterMatches(filter);
        });
    });
    
    // User select change
    const userSelect = document.getElementById('cf-user-select');
    if (userSelect) {
        userSelect.addEventListener('change', async (e) => {
            currentUserId = e.target.value ? parseInt(e.target.value) : null;
            if (currentUserId) {
                const user = allUsers.find(u => u.id === currentUserId) || await api.getUserById(currentUserId);
                api.setCurrentProfile(currentUserId, user?.name || null);
                if (user) updateSelectedProfileSummary(user);
            }
        });
    }
    
    // Idea selector change
    const ideaSelector = document.getElementById('idea-selector');
    if (ideaSelector) {
        ideaSelector.addEventListener('change', async (e) => {
            const ideaId = parseInt(e.target.value);
            if (ideaId) {
                await handleIdeaSelection(ideaId);
            }
        });
    }
}

/**
 * Handle profile creation form submission
 */
function setupCreateProfileForm() {
    const form = document.getElementById('cf-create-form');
    if (!form) return;
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const statusEl = document.getElementById('cf-create-status');
        try {
            const name = document.getElementById('cf-name')?.value.trim();
            const email = document.getElementById('cf-email')?.value.trim();
            const location = document.getElementById('cf-location')?.value.trim();
            const interest = document.getElementById('cf-interest')?.value.trim();
            const personality = document.getElementById('cf-personality')?.value.trim();
            const commitmentRaw = document.getElementById('cf-commit')?.value.trim();
            const commit = commitmentRaw ? Math.min(1, Math.max(0, parseFloat(commitmentRaw))) : null;
            const skillsRaw = document.getElementById('cf-skills')?.value.trim();
            const skills = skillsRaw ? skillsRaw.split(',').map(s => s.trim()).filter(Boolean) : [];
            if (!name || !email) {
                statusEl.innerHTML = '<span class="text-red-400">Name & Email required</span>';
                return;
            }
            statusEl.innerHTML = '<span class="text-pink-300"><i class="fas fa-spinner fa-spin"></i> Saving...</span>';
            const profile = await api.createUserProfile({
                name, email, location, interest, personality, commitment_level: commit, skills
            });
            statusEl.innerHTML = '<span class="text-green-400">✅ Profile saved!</span>';
            // Refresh user selector
            await loadUsers();
            const select = document.getElementById('cf-user-select');
            if (select && profile.id) {
                select.value = profile.id;
                currentUserId = profile.id;
                api.setCurrentProfile(profile.id, profile.name);
                updateSelectedProfileSummary(profile);
            }
        } catch (err) {
            console.error('Profile create error', err);
            statusEl.innerHTML = '<span class="text-red-400">Failed to save profile</span>';
        }
    });
}

function updateSelectedProfileSummary(user){
    const initials = (user.name || '').split(' ').map(s=>s[0]).join('').slice(0,2).toUpperCase() || '--';
    const sub = user.interest || user.location || '';
    const nameEl = document.getElementById('cf-name');
    const initialsEl = document.getElementById('cf-initials');
    const subEl = document.getElementById('cf-sub');
    if (nameEl) nameEl.textContent = user.name || 'Profile';
    if (initialsEl) initialsEl.textContent = initials;
    if (subEl) subEl.textContent = sub;
}

/**
 * Handle find matches button click
 */
async function handleFindMatches() {
    if (!currentUserId) {
        // Show visual feedback instead of just console error
        const userSelect = document.getElementById('cf-user-select');
        if (userSelect) {
            userSelect.style.border = '2px solid #ef4444';
            userSelect.style.animation = 'shake 0.5s';
            setTimeout(() => {
                userSelect.style.border = '';
                userSelect.style.animation = '';
            }, 1000);
        }
        
        showError('⚠️ Please select your profile from the dropdown first!');
        
        // Highlight the dropdown with a pulsing effect
        const instructionsEl = document.getElementById('cf-instructions');
        if (instructionsEl) {
            instructionsEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        
        return;
    }
    
    const findBtn = document.getElementById('cf-find-btn');
    const originalText = findBtn.textContent;
    
    try {
        // Show loading state
        findBtn.disabled = true;
        findBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>AI Headhunter Searching...';
        
        // Hide static samples
        hideStaticSamples();
        
        // Get the current user's data to build an "idea" from their profile
        const user = allUsers.find(u => u.id === currentUserId);
        if (!user) {
            throw new Error('User profile not found');
        }
        
        // Build a synthetic "idea" from user's interests and skills
        const skills = (user.skills || []).map(s => s.name).join(', ');
        const syntheticIdea = `I'm looking for cofounders for a ${user.interest || 'tech'} startup. I bring expertise in ${skills || 'various skills'} and I'm based in ${user.location || 'remote'}. Looking for complementary skills to build a strong founding team.`;
        
        console.log(`🔍 Using AI Headhunter with synthetic idea from profile`);
        console.log(`📝 Idea: ${syntheticIdea}`);
        
        // Call the NEW AI matching API
        const matches = await api.findCofoundersByIdea(syntheticIdea, 10);
        currentMatches = matches;
        
        console.log(`✅ AI Headhunter found ${matches.length} matches`);
        
        // Transform and display matches (they're already in AI format)
        const transformedMatches = matches.map(match => ({
            user: {
                id: match.id,
                name: match.name,
                username: match.username,
                location: match.location,
                interest: (match.interests || []).join(', '),
                bio: match.bio,
                skills: (match.skills || []).map(s => ({ name: s })),
                avatar_url: match.avatar_url,
                profile_url: match.profile_url,
                role_type: match.role_type,
                source: match.source
            },
            score: match.match_percentage,
            synergy_analysis: match.synergy_analysis,
            missing_skills_filled: match.missing_skills_filled,
            recommended_action: match.recommended_action,
            intro_message: match.intro_message
        }));
        
        displayMatches(transformedMatches);
        
        // Update stats
        updateStatsWithMatches(transformedMatches);
        
    } catch (error) {
        console.error('Failed to find matches:', error);
        showError('AI Headhunter search failed: ' + error.message);
    } finally {
        findBtn.disabled = false;
        findBtn.textContent = originalText;
    }
}

/**
 * Find cofounders based on a startup idea (NEW: Real matching engine)
 * This function is called from other pages (like dashboard) with an idea description
 */
window.findCofoundersByIdea = async function(ideaText, topK = 10, excludeUserId = null) {
    // NEW: Hybrid profiles become the default path.
    console.log('🧠 Hybrid matching (GitHub + AI personas) for idea:', ideaText.substring(0,80),'...');
    const dynamicContainer = document.getElementById('cf-matches-dynamic');
    if (dynamicContainer) {
        // Clear out any static dummy content immediately
        hideStaticSamples();
        dynamicContainer.innerHTML = `<div class="text-center py-12"><div class="text-6xl mb-4 animate-spin">🧠</div><h3 class="text-2xl font-bold text-gray-300 mb-2">Curating Hybrid Founder Profiles...</h3><p class="text-gray-400">Analyzing your idea + compiling real & synthetic candidates</p></div>`;
    }
    // Delegate to hybrid loader (already sets currentMatches & renders)
    return await loadHybridProfiles(ideaText, topK);
};

// =============================================================
// SMART OUTREACH MODAL
// =============================================================
async function showSmartOutreachModal(match) {
        const user = match.user;
        const ideaText = sessionStorage.getItem('matchingIdea') || 'a high-impact startup concept';
        // Skeleton modal
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4';
        modal.innerHTML = `
            <div class="bg-[#150a24] border border-purple-500/30 w-full max-w-lg rounded-2xl shadow-2xl shadow-purple-900/50 overflow-hidden animate-fadeIn">
                <div class="p-5 border-b border-white/5 flex justify-between items-center bg-white/5">
                    <div class="flex items-center gap-3">
                        <img src="${user.avatar_url}" class="w-10 h-10 rounded-full border border-purple-400" alt="${user.name}">
                        <div>
                            <h3 class="text-white font-bold">Connect with ${user.name}</h3>
                            <p class="text-xs text-purple-300">AI Drafted Icebreaker</p>
                        </div>
                    </div>
                    <button id="outreach-close" class="text-gray-400 hover:text-white transition-colors">✕</button>
                </div>
                <div class="p-6" id="outreach-body">
                    <div class="py-12 flex flex-col items-center justify-center text-purple-300 space-y-3" id="outreach-loading">
                        <div class="w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full animate-spin"></div>
                        <p class="text-sm animate-pulse">Analyzing ${user.name.split(' ')[0]}'s profile...</p>
                    </div>
                </div>
            </div>`;
        document.body.appendChild(modal);
        const bodyEl = modal.querySelector('#outreach-body');
        // Fetch draft
        let draft = '';
        try {
                const resp = await fetch('/matching/outreach-draft', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                                user_role: 'Founder',
                                profile_role: user.role_type || 'Contributor',
                                profile_name: user.name,
                                profile_bio: user.bio,
                                user_idea: ideaText
                        })
                });
                const data = await resp.json();
                draft = data.draft_message || `Hi ${user.name.split(' ')[0]}, building ${ideaText.substring(0,60)} – your ${user.role_type} experience looks like a strong fit. Open to a quick chat?`;
        } catch (err) {
                draft = `Hi ${user.name.split(' ')[0]}, exploring ${ideaText.substring(0,50)} – your background seems very complementary. Would love to connect!`;
        }
        bodyEl.innerHTML = `
            <div class="space-y-4">
                <textarea id="outreach-text" class="w-full h-32 bg-[#090014] border border-purple-500/30 rounded-lg p-4 text-gray-200 text-sm focus:outline-none focus:border-purple-500">${draft}</textarea>
                <div class="flex gap-3">
                    <button id="outreach-cancel" class="flex-1 py-2 rounded-lg text-gray-400 hover:bg-white/5 text-sm transition-colors">Cancel</button>
                    <button id="outreach-send" class="flex-1 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-sm font-semibold flex items-center justify-center gap-2 shadow-lg shadow-purple-900/20">Send</button>
                </div>
            </div>`;
        return new Promise(resolve => {
                bodyEl.querySelector('#outreach-cancel').onclick = () => { modal.remove(); resolve(false); };
                bodyEl.querySelector('#outreach-send').onclick = async () => {
                        const btn = bodyEl.querySelector('#outreach-send');
                        btn.disabled = true; btn.textContent = 'Sending...';
                        // Simulate invite via backend connect-invite endpoint
                        try { await fetch('/matching/connect-invite', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ profile_name: user.name, user_idea: ideaText })}); } catch {}
                        setTimeout(()=>{ btn.textContent='Sent ✅'; setTimeout(()=>{ modal.remove(); resolve(true); },800); },600);
                };
                modal.querySelector('#outreach-close').onclick = () => { modal.remove(); resolve(false); };
        });
}

/**
 * Display matches in the UI
 */
function displayMatches(matches) {
    console.log('📺 displayMatches called with', matches.length, 'matches');
    
    const dynamicContainer = document.getElementById('cf-matches-dynamic');
    const instructionsEl = document.getElementById('cf-instructions');
    console.log('📺 Container element:', dynamicContainer ? 'FOUND' : 'NOT FOUND');
    
    if (!dynamicContainer) {
        console.error('❌ Container cf-matches-dynamic not found!');
        return;
    }
    
    // Ensure any hardcoded static sample cards are hidden
    hideStaticSamples();

    // Hide instructions once matches are shown
    if (instructionsEl) {
        instructionsEl.style.display = 'none';
    }
    
    if (matches.length === 0) {
        console.log('⚠️ No matches to display');
        dynamicContainer.innerHTML = `
            <div class="text-center py-12">
                <div class="text-6xl mb-4">🤷</div>
                <h3 class="text-2xl font-bold text-gray-300 mb-2">No Matches Found</h3>
                <p class="text-gray-400">Try creating a more detailed profile or check back later!</p>
                <a href="/profile-setup" class="cta-button inline-block mt-6 text-white font-bold py-3 px-6 rounded-lg">
                    Update Your Profile
                </a>
            </div>
        `;
        return;
    }
    
    console.log('✅ Rendering', matches.length, 'match cards');
    dynamicContainer.innerHTML = matches.map(match => createMatchCard(match)).join('');
    console.log('✅ HTML rendered. Container HTML length:', dynamicContainer.innerHTML.length);
    
    // Animate entrance
    gsap.from('#cf-matches-dynamic > *', {
        y: 30,
        opacity: 0,
        duration: 0.5,
        stagger: 0.1,
        ease: 'power2.out'
    });
}

/**
 * Create match card HTML
 */
function createMatchCard(match) {
    const user = match.user;
    const score = Math.round(match.score);
    
    // Determine match level based on AI recommended action
    let matchLevel, matchBadge, badgeClass;
    const action = match.recommended_action || 'Explore';
    
    if (action === 'Must Connect' || score >= 80) {
        matchLevel = 'premium-match';
        matchBadge = '<i class="fas fa-crown"></i> MUST CONNECT';
        badgeClass = 'premium-badge';
    } else if (action === 'Strong Option' || score >= 60) {
        matchLevel = 'high-match';
        matchBadge = '<i class="fas fa-star"></i> STRONG OPTION';
        badgeClass = 'high-badge';
    } else if (action === 'Explore' || score >= 40) {
        matchLevel = 'good-match';
        matchBadge = '<i class="fas fa-lightbulb"></i> EXPLORE';
        badgeClass = 'good-badge';
    } else {
        matchLevel = 'potential-match';
        matchBadge = '<i class="fas fa-search"></i> REVIEW';
        badgeClass = 'potential-badge';
    }
    
    // Get user avatar (real GitHub avatar or placeholder)
    const avatar = user.avatar_url || `https://ui-avatars.com/api/?name=${encodeURIComponent(user.name)}&background=random&size=80`;
    
    // Determine if this is a GitHub profile
    const isGitHub = user.source === 'github';
    const profileBadge = isGitHub 
        ? '<span class="inline-flex items-center gap-1 px-2 py-1 bg-gray-900 border border-gray-700 rounded text-xs text-gray-300"><svg height="12" width="12" viewBox="0 0 16 16" fill="currentColor"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"></path></svg> GitHub</span>'
        : '<span class="inline-flex items-center gap-1 px-2 py-1 bg-purple-900/50 border border-purple-700/50 rounded text-xs text-purple-300"><svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg> Local</span>';
    
    // Get skills
    const skills = user.skills || [];
    const skillsHtml = skills.length > 0 
        ? skills.slice(0, 4).map(s => `<div class="skill-tag">🔧 ${s.name}</div>`).join('')
        : '<div class="text-gray-500 text-sm">No skills listed</div>';
    
    // AI role type
    const roleType = user.role_type || 'Entrepreneur';
    
    // AI Synergy Analysis
    const synergyAnalysis = match.synergy_analysis || null;
    
    // Missing skills filled by this candidate
    const missingSkills = match.missing_skills_filled || [];
    const missingSkillsHtml = missingSkills.length > 0 
        ? `<div class="bg-green-500/10 border border-green-400/30 rounded-lg p-3 mb-3">
            <div class="text-xs font-semibold text-green-300 mb-2">💡 Critical Skills They Bring:</div>
            <div class="flex flex-wrap gap-2">
                ${missingSkills.map(skill => `<span class="px-2 py-1 bg-green-500/20 text-green-200 rounded text-xs">${skill}</span>`).join('')}
            </div>
        </div>`
        : '';
    
    // Force fallback social links for demo polish
    const githubLink = (user.profile_url && user.profile_url.startsWith('http'))
        ? user.profile_url
        : `https://github.com/search?q=${encodeURIComponent((user.name || 'founder').replace(/\s+/g,''))}`;
    const linkedinLink = (user.linkedin_url && user.linkedin_url.startsWith('http'))
        ? user.linkedin_url
        : `https://www.linkedin.com/search/results/people/?keywords=${encodeURIComponent(user.name || 'Founder')}`;

    return `
        <div class="match-card ${matchLevel}" style="background:#130b20" data-category="${categorizeUser(user)}" data-user-id="${user.id}" tabindex="0" role="button" aria-label="View ${user.name} profile">
            <div class="match-badge ${badgeClass}">
                ${matchBadge}
            </div>
            <div class="match-compatibility">
                <div class="compatibility-score">${score}%</div>
                <div class="compatibility-label">AI Match</div>
            </div>
            
            <div class="match-content">
                <div class="match-avatar-section">
                    <div class="match-avatar">
                        <img src="${avatar}" alt="${user.name}" onerror="this.src='https://ui-avatars.com/api/?name=${encodeURIComponent(user.name)}&background=6366f1&color=fff&size=80'">
                        ${isGitHub ? '<div class="absolute -bottom-1 -right-1 w-6 h-6 bg-gray-900 rounded-full border-2 border-purple-500 flex items-center justify-center"><svg height="12" width="12" viewBox="0 0 16 16" fill="#ffffff"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"></path></svg></div>' : ''}
                    </div>
                    <div class="match-basic-info">
                        <h3 class="match-name">${user.name}</h3>
                        ${user.username ? `<div class="text-sm text-gray-400">@${user.username}</div>` : ''}
                        <div class="flex items-center gap-2 mt-1">
                            <div class="match-title">${roleType}</div>
                            ${profileBadge}
                        </div>
                        <div class="match-location">
                            <i class="fas fa-map-marker-alt"></i>
                            ${user.location || 'Location not specified'}
                        </div>
                    </div>
                </div>

                <div class="match-details">
                    <div class="match-bio">
                        "${user.personality || user.bio || generateBio(user)}"
                    </div>
                    
                    ${synergyAnalysis ? `
                        <div class="bg-purple-500/10 border border-purple-400/30 rounded-lg p-3 mb-3">
                            <div class="text-xs font-semibold text-purple-300 mb-1">🎯 Why This Is a Great Match:</div>
                            <div class="text-sm text-gray-300">${synergyAnalysis}</div>
                        </div>
                    ` : ''}
                    
                    ${missingSkillsHtml}
                    
                    <div class="match-skills">
                        ${skillsHtml}
                    </div>

                    <div class="match-actions">
                        <button class="match-action-btn primary" onclick="connectWithUser('${user.id}', '${user.name}')">
                            <i class="fas fa-handshake"></i> Connect
                        </button>
                        <div class="flex gap-2 flex-wrap mt-2">
                            <a href="${githubLink}" target="_blank" rel="noopener noreferrer" class="match-action-btn secondary" style="text-decoration:none;display:inline-flex;align-items:center;justify-content:center;" title="GitHub Profile">
                                <svg height="14" width="14" viewBox="0 0 16 16" fill="currentColor" class="mr-1"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"></path></svg>
                                GitHub
                            </a>
                            <a href="${linkedinLink}" target="_blank" rel="noopener noreferrer" class="match-action-btn secondary" style="text-decoration:none;display:inline-flex;align-items:center;justify-content:center;background:#0077b5;" title="LinkedIn Profile">
                                <svg height="14" width="14" viewBox="0 0 24 24" fill="#ffffff" class="mr-1"><path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.926-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/></svg>
                                LinkedIn
                            </a>
                            <button class="match-action-btn tertiary" onclick="saveMatch('${user.id}')">
                                <i class="fas fa-bookmark"></i> Save
                            </button>
                            <button class="match-action-btn secondary" onclick="viewUserProfile('${user.id}')">
                                <i class="fas fa-eye"></i> Details
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

/**
 * Categorize user based on skills/interest
 */
function categorizeUser(user) {
    const interest = (user.interest || '').toLowerCase();
    const skills = (user.skills || []).map(s => s.name.toLowerCase());
    
    // Check for technical indicators
    const techKeywords = ['engineer', 'developer', 'ai', 'ml', 'tech', 'software', 'data', 'python', 'javascript'];
    if (techKeywords.some(k => interest.includes(k) || skills.some(s => s.includes(k)))) {
        return 'technical';
    }
    
    // Check for business indicators
    const bizKeywords = ['business', 'strategy', 'finance', 'marketing', 'sales', 'product', 'management'];
    if (bizKeywords.some(k => interest.includes(k) || skills.some(s => s.includes(k)))) {
        return 'business';
    }
    
    // Check for design indicators
    const designKeywords = ['design', 'ui', 'ux', 'creative', 'brand', 'visual'];
    if (designKeywords.some(k => interest.includes(k) || skills.some(s => s.includes(k)))) {
        return 'design';
    }
    
    return 'other';
}

/**
 * Generate bio from user data
 */
function generateBio(user) {
    const interest = user.interest || 'general innovation';
    const skills = (user.skills || []).slice(0, 3).map(s => s.name).join(', ') || 'various skills';
    const commitment = user.commitment_level 
        ? user.commitment_level > 0.7 ? 'full-time' : 'part-time'
        : 'flexible';
    
    const templates = [
        `Passionate about ${interest}. Expert in ${skills}. Looking for a ${commitment} cofounder to build something amazing.`,
        `${commitment.charAt(0).toUpperCase() + commitment.slice(1)} entrepreneur focused on ${interest}. Brings expertise in ${skills}.`,
        `Seeking cofounder for ${interest} venture. Skills include ${skills}. Available ${commitment}.`,
        `Experienced in ${interest} with strong ${skills} background. Ready for ${commitment} commitment.`
    ];
    // Choose the first template deterministically to avoid random/fake variation
    return templates[0];
}

/**
 * Filter matches by category
 */
function filterMatches(filter) {
    const matchCards = document.querySelectorAll('.match-card:not(.static-sample)');
    
    matchCards.forEach(card => {
        if (filter === 'all') {
            card.style.display = 'block';
        } else {
            const category = card.dataset.category;
            card.style.display = category === filter ? 'block' : 'none';
        }
    });
    
    // Animate visible cards
    const visibleCards = Array.from(matchCards).filter(c => c.style.display === 'block');
    gsap.from(visibleCards, {
        y: 20,
        opacity: 0,
        duration: 0.4,
        stagger: 0.05,
        ease: 'power2.out'
    });

    // Attach click/keyboard handlers (idempotent - reattaching harmless)
    visibleCards.forEach(card => {
        card.onclick = () => {
            const id = parseInt(card.getAttribute('data-user-id'), 10);
            if (!isNaN(id)) window.viewUserProfile(id);
        };
        card.onkeydown = (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); card.click(); } };
    });
}

/**
 * Hide static sample cards
 */
function hideStaticSamples() {
    const staticCards = document.querySelectorAll('.static-sample');
    staticCards.forEach(card => {
        card.style.display = 'none';
    });
}

/**
 * Connect with a user
 */
window.connectWithUser = async function(userId, userName) {
    try {
        // Get current user ID from JWT
        const token = localStorage.getItem('access_token');
        if (!token) {
            alert('Please log in to connect with cofounders');
            window.location.href = '/login';
            return;
        }
        
        const payload = JSON.parse(atob(token.split('.')[1]));
        const currentUserId = payload.sub;
        
        // Smart outreach modal first
        const matchObj = currentMatches.find(m => m.user.id == userId);
        const proceed = await showSmartOutreachModal(matchObj || { user: { name: userName, role_type:'Contributor' }});
        if (!proceed) return;
        const introMessage = (matchObj?.intro_message) || `Hi ${userName}, I saw your profile on Elevare and think we could build something great together!`;
        // Actual connection request (existing endpoint)
        const response = await fetch('/api/connect/send', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                sender_id: parseInt(currentUserId),
                recipient_id: parseInt(userId),
                message: introMessage,
                idea_context: sessionStorage.getItem('matchingIdeaTitle') || null
            })
        });
        
        if (!response.ok) {
            throw new Error('Connection request failed');
        }
        
        const result = await response.json();
        
        if (result.success) {
            // Show success with contact method
            if (result.connection_method === 'email') {
                api.showSuccess(`📧 Connection request sent to ${userName} via email!`);
            } else if (result.connection_method === 'linkedin') {
                window.open(result.contact_info, '_blank');
                api.showSuccess(`Opening LinkedIn profile for ${userName}...`);
            } else if (result.connection_method === 'github') {
                window.open(result.contact_info, '_blank');
                api.showSuccess(`Opening GitHub profile for ${userName}...`);
            }
        } else {
            api.showError(result.message || 'No contact information available');
        }
        
        console.log(`✅ Connect attempt: ${result.connection_method} - ${userName}`);
    } catch (error) {
        console.error('Failed to connect:', error);
        api.showError('Failed to send connection request. Please try again.');
    }
};

/**
 * View user profile
 */
window.viewUserProfile = function(userId) {
    const user = allUsers.find(u => u.id === userId) || 
                 currentMatches.find(m => m.user.id === userId)?.user;
    
    if (!user) {
        showError('User not found');
        return;
    }
    
    // Create profile modal
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4';
    modal.innerHTML = `
        <div class="bg-gradient-to-br from-gray-900 to-black border border-purple-400/30 rounded-3xl p-8 max-w-2xl w-full">
            <div class="flex items-center justify-between mb-6">
                <h2 class="text-3xl font-bold">
                    <span class="holographic-text-pro">${user.name}</span>
                </h2>
                <button onclick="this.closest('.fixed').remove()" class="text-gray-400 hover:text-white text-3xl">×</button>
            </div>
            
            <div class="space-y-6">
                <div>
                    <h3 class="text-lg font-bold text-purple-300 mb-2">Interest</h3>
                    <p class="text-gray-300">${user.interest || 'Not specified'}</p>
                </div>
                
                <div>
                    <h3 class="text-lg font-bold text-purple-300 mb-2">Location</h3>
                    <p class="text-gray-300">${user.location || 'Not specified'}</p>
                </div>
                
                <div>
                    <h3 class="text-lg font-bold text-purple-300 mb-2">Skills</h3>
                    <div class="flex flex-wrap gap-2">
                        ${(user.skills || []).map(s => `
                            <span class="px-3 py-1 bg-purple-500/20 border border-purple-400/30 rounded-full text-sm text-purple-300">
                                ${s.name}
                            </span>
                        `).join('') || '<p class="text-gray-500">No skills listed</p>'}
                    </div>
                </div>
                
                <div>
                    <h3 class="text-lg font-bold text-purple-300 mb-2">Commitment Level</h3>
                    <div class="flex items-center gap-4">
                        <div class="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
                            <div class="h-full bg-gradient-to-r from-purple-500 to-pink-500" style="width: ${(user.commitment_level || 0.5) * 100}%"></div>
                        </div>
                        <span class="text-gray-300">${Math.round((user.commitment_level || 0.5) * 100)}%</span>
                    </div>
                </div>
                
                <div class="flex gap-4 pt-4">
                    <button onclick="connectWithUser(${user.id}, '${user.name}')" class="flex-1 px-6 py-3 bg-gradient-to-r from-purple-500 to-pink-500 rounded-xl font-bold text-white hover:scale-105 transition-transform">
                        <i class="fas fa-heart mr-2"></i>Send Connection Request
                    </button>
                    <button onclick="this.closest('.fixed').remove()" class="px-6 py-3 border border-gray-600 rounded-xl font-bold text-gray-300 hover:border-gray-400 transition-colors">
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
 * Save match for later
 */
window.saveMatch = function(userId) {
    const user = currentMatches.find(m => m.user.id === userId)?.user;
    if (!user) return;
    
    // Save to localStorage
    const savedMatches = JSON.parse(localStorage.getItem('savedMatches') || '[]');
    if (!savedMatches.includes(userId)) {
        savedMatches.push(userId);
        localStorage.setItem('savedMatches', JSON.stringify(savedMatches));
        api.showSuccess(`Saved ${user.name} to your bookmarks! 📌`);
    } else {
        api.showSuccess(`${user.name} is already in your bookmarks`);
    }
};

/**
 * Show connect confirmation modal
 */
function showConnectModal(userName) {
    return new Promise((resolve) => {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4';
        modal.innerHTML = `
            <div class="bg-gradient-to-br from-gray-900 to-black border border-pink-400/30 rounded-3xl p-8 max-w-md w-full">
                <div class="text-center">
                    <div class="text-6xl mb-4">💕</div>
                    <h2 class="text-2xl font-bold mb-4">
                        <span class="holographic-text-pro">Send Connection?</span>
                    </h2>
                    <p class="text-gray-300 mb-6">
                        Send a collaboration request to <strong class="text-pink-300">${userName}</strong>?
                    </p>
                    <div class="flex gap-4">
                        <button id="confirm-connect" class="flex-1 px-6 py-3 bg-gradient-to-r from-pink-500 to-rose-500 rounded-xl font-bold text-white hover:scale-105 transition-transform">
                            Yes, Connect! 🚀
                        </button>
                        <button id="cancel-connect" class="flex-1 px-6 py-3 border border-gray-600 rounded-xl font-bold text-gray-300 hover:border-gray-400 transition-colors">
                            Cancel
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        document.getElementById('confirm-connect').onclick = () => {
            modal.remove();
            resolve(true);
        };
        
        document.getElementById('cancel-connect').onclick = () => {
            modal.remove();
            resolve(false);
        };
        
        gsap.from(modal.querySelector('div'), {
            scale: 0.9,
            opacity: 0,
            duration: 0.3
        });
    });
}

/**
 * Update stats with real data
 */
function updateStats() {
    const compatEl = document.getElementById('compat-count');
    if (compatEl) animateNumber(compatEl, allUsers.length);
}

/**
 * Update stats based on matches found
 */
function updateStatsWithMatches(matches) {
    const highMatchesEl = document.getElementById('high-matches');
    const highMatches = matches.filter(m => m.score >= 75).length;
    if (highMatchesEl) animateNumber(highMatchesEl, highMatches);
}

/**
 * Animate number counting
 */
function animateNumber(element, targetValue) {
    const startValue = parseInt(element.textContent.replace(/,/g, '')) || 0;
    const duration = 1000;
    const startTime = Date.now();
    
    function update() {
        const now = Date.now();
        const progress = Math.min((now - startTime) / duration, 1);
        const currentValue = Math.floor(startValue + (targetValue - startValue) * progress);
        element.textContent = currentValue.toLocaleString();
        
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    
    update();
}

/**
 * Animate page entrance
 */
function animatePageEntrance() {
    gsap.from('.match-stat-card', {
        y: 30,
        opacity: 0,
        duration: 0.6,
        stagger: 0.1,
        ease: 'power2.out',
        delay: 0.2
    });
    
    gsap.from('.cofounder-card-pro', {
        y: 40,
        opacity: 0,
        duration: 0.7,
        stagger: 0.15,
        ease: 'power2.out',
        delay: 0.4
    });
}

/**
 * Create cofounder particles
 */
function createCofounderParticles() {
    const container = document.getElementById('cofounder-particles');
    if (!container) return;
    
    for (let i = 0; i < 40; i++) {
        const particle = document.createElement('div');
        particle.className = 'cofounder-particle';
        particle.style.left = Math.random() * 100 + '%';
        particle.style.top = Math.random() * 100 + '%';
        particle.style.animationDelay = Math.random() * 20 + 's';
        container.appendChild(particle);
    }
}

/**
 * Show error message
 */
function showError(message) {
    api.showError(message);
}

/**
 * Logout function
 */
function logout() {
    if (confirm('Are you sure you want to logout?')) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('token_type');
        sessionStorage.clear();
        window.location.href = '/login';
    }
}

/**
 * Auto-load current user from token
 */
async function loadCurrentUserHeader() {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        const userId = payload.sub;

        const response = await fetch(`/matching/users/${userId}`);
        if (response.ok) {
            const user = await response.json();
            const initials = user.name.split(' ').map(n => n[0]).join('').toUpperCase();
            const nameEl = document.getElementById('cf-header-name');
            const initialsEl = document.getElementById('cf-header-initials');
            if (nameEl) nameEl.textContent = user.name;
            if (initialsEl) initialsEl.textContent = initials;
        }
    } catch (error) {
        console.error('Error loading user header:', error);
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        initializeCofounderPage();
        loadCurrentUserHeader();
    });
} else {
    initializeCofounderPage();
    loadCurrentUserHeader();
}
