// API Base URL
const API_BASE = window.location.origin;

// Tab switching
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const tabName = btn.dataset.tab;
        
        // Update buttons
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        
        // Update content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(tabName).classList.add('active');
    });
});

// Idea Validator Form
document.getElementById('idea-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const rawIdea = document.getElementById('raw-idea').value;
    const submitBtn = e.target.querySelector('button[type="submit"]');
    const btnText = submitBtn.querySelector('.btn-text');
    const spinner = submitBtn.querySelector('.spinner');
    const resultsDiv = document.getElementById('idea-results');
    const errorDiv = document.getElementById('idea-error');
    
    // Show loading state
    submitBtn.disabled = true;
    btnText.textContent = 'Analyzing...';
    spinner.style.display = 'inline-block';
    resultsDiv.style.display = 'none';
    errorDiv.style.display = 'none';
    
    try {
        const response = await fetch(`${API_BASE}/refine-idea`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                raw_idea_text: rawIdea
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to validate idea');
        }
        
        const data = await response.json();
        displayIdeaResults(data);
        resultsDiv.style.display = 'block';
        
    } catch (error) {
        errorDiv.textContent = `Error: ${error.message}`;
        errorDiv.style.display = 'block';
    } finally {
        submitBtn.disabled = false;
        btnText.textContent = 'Validate Idea';
        spinner.style.display = 'none';
    }
});

function displayIdeaResults(data) {
    const refined = data.refined_idea;
    const market = data.market_profile;
    
    // Overall score
    document.getElementById('overall-score').textContent = data.overall_confidence_score.toFixed(1);
    
    // Refined idea details
    document.getElementById('idea-title').textContent = refined.idea_title;
    document.getElementById('core-domain').textContent = refined.core_domain;
    document.getElementById('location').textContent = refined.suggested_location || 'Global';
    document.getElementById('feasibility-score').textContent = refined.initial_feasibility_score.toFixed(1);
    document.getElementById('problem-statement').textContent = refined.problem_statement;
    document.getElementById('solution-concept').textContent = refined.solution_concept;
    document.getElementById('target-user').textContent = refined.target_user;
    
    // Suggestions
    const suggestionsList = document.getElementById('suggestions-list');
    suggestionsList.innerHTML = '';
    refined.nlp_suggestions.forEach(suggestion => {
        const li = document.createElement('li');
        li.textContent = suggestion;
        suggestionsList.appendChild(li);
    });
    
    // Market analysis
    document.getElementById('market-score').textContent = market.market_viability_score.toFixed(1);
    document.getElementById('trend-score').textContent = market.raw_trend_score !== null ? market.raw_trend_score.toFixed(2) : 'N/A';
    document.getElementById('competitor-count').textContent = market.raw_competitor_count !== null ? market.raw_competitor_count : 'N/A';
    document.getElementById('market-rationale').textContent = market.rationale;
}

// User Creation Form
document.getElementById('user-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const submitBtn = e.target.querySelector('button[type="submit"]');
    const btnText = submitBtn.querySelector('.btn-text');
    const spinner = submitBtn.querySelector('.spinner');
    const successDiv = document.getElementById('user-success');
    const errorDiv = document.getElementById('user-error');
    
    const skills = document.getElementById('user-skills').value
        .split(',')
        .map(s => s.trim())
        .filter(s => s);
    
    const commitmentValue = document.getElementById('user-commitment').value;
    
    const userData = {
        name: document.getElementById('user-name').value,
        email: document.getElementById('user-email').value,
        location: document.getElementById('user-location').value || null,
        interest: document.getElementById('user-interest').value || null,
        personality: document.getElementById('user-personality').value || null,
        commitment_level: commitmentValue ? parseFloat(commitmentValue) : null,
        skills: skills.length > 0 ? skills : null
    };
    
    // Show loading state
    submitBtn.disabled = true;
    btnText.textContent = 'Creating...';
    spinner.style.display = 'inline-block';
    successDiv.style.display = 'none';
    errorDiv.style.display = 'none';
    
    try {
        const response = await fetch(`${API_BASE}/matching/users`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(userData)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create user');
        }
        
        const data = await response.json();
        successDiv.textContent = `User created successfully! ID: ${data.id}`;
        successDiv.style.display = 'block';
        e.target.reset();
        
    } catch (error) {
        errorDiv.textContent = `Error: ${error.message}`;
        errorDiv.style.display = 'block';
    } finally {
        submitBtn.disabled = false;
        btnText.textContent = 'Create Profile';
        spinner.style.display = 'none';
    }
});

// Load Users
document.getElementById('load-users-btn').addEventListener('click', async () => {
    const btn = document.getElementById('load-users-btn');
    const usersListDiv = document.getElementById('users-list');
    
    btn.disabled = true;
    btn.textContent = 'Loading...';
    
    try {
        const response = await fetch(`${API_BASE}/matching/users`);
        
        if (!response.ok) {
            throw new Error('Failed to load users');
        }
        
        const users = await response.json();
        displayUsers(users);
        
    } catch (error) {
        usersListDiv.innerHTML = `<p class="error-message">Error: ${error.message}</p>`;
    } finally {
        btn.disabled = false;
        btn.textContent = 'Load Users';
    }
});

function displayUsers(users) {
    const usersListDiv = document.getElementById('users-list');
    
    if (users.length === 0) {
        usersListDiv.innerHTML = '<p>No users found. Create a profile to get started!</p>';
        return;
    }
    
    usersListDiv.innerHTML = users.map(user => `
        <div class="user-card">
            <h4>${user.name} (ID: ${user.id})</h4>
            <p><strong>Email:</strong> ${user.email}</p>
            ${user.location ? `<p><strong>Location:</strong> ${user.location}</p>` : ''}
            ${user.interest ? `<p><strong>Interest:</strong> ${user.interest}</p>` : ''}
            ${user.personality ? `<p><strong>Personality:</strong> ${user.personality}</p>` : ''}
            ${user.commitment_level !== null ? `<p><strong>Commitment:</strong> ${user.commitment_level}</p>` : ''}
            ${user.skills && user.skills.length > 0 ? `
                <div class="skills-list">
                    ${user.skills.map(skill => `<span class="skill-tag">${skill.name}</span>`).join('')}
                </div>
            ` : ''}
        </div>
    `).join('');
}

// Find Matches
document.getElementById('find-matches-btn').addEventListener('click', async () => {
    const userId = document.getElementById('match-user-id').value;
    const btn = document.getElementById('find-matches-btn');
    const matchesListDiv = document.getElementById('matches-list');
    
    if (!userId) {
        matchesListDiv.innerHTML = '<p class="error-message">Please enter a user ID</p>';
        return;
    }
    
    btn.disabled = true;
    btn.textContent = 'Finding Matches...';
    
    try {
        const response = await fetch(`${API_BASE}/matching/matches/${userId}`);
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to find matches');
        }
        
        const matches = await response.json();
        displayMatches(matches);
        
    } catch (error) {
        matchesListDiv.innerHTML = `<p class="error-message">Error: ${error.message}</p>`;
    } finally {
        btn.disabled = false;
        btn.textContent = 'Find Matches';
    }
});

function displayMatches(matches) {
    const matchesListDiv = document.getElementById('matches-list');
    
    if (matches.length === 0) {
        matchesListDiv.innerHTML = '<p>No matches found. Try creating more user profiles!</p>';
        return;
    }
    
    matchesListDiv.innerHTML = matches.map(match => `
        <div class="match-card">
            <h4>${match.user.name} (ID: ${match.user.id})</h4>
            <span class="match-score">Match Score: ${match.score.toFixed(2)}</span>
            <p><strong>Email:</strong> ${match.user.email}</p>
            ${match.user.location ? `<p><strong>Location:</strong> ${match.user.location}</p>` : ''}
            ${match.user.interest ? `<p><strong>Interest:</strong> ${match.user.interest}</p>` : ''}
            ${match.user.personality ? `<p><strong>Personality:</strong> ${match.user.personality}</p>` : ''}
            ${match.user.commitment_level !== null ? `<p><strong>Commitment:</strong> ${match.user.commitment_level}</p>` : ''}
            ${match.user.skills && match.user.skills.length > 0 ? `
                <div class="skills-list">
                    ${match.user.skills.map(skill => `<span class="skill-tag">${skill.name}</span>`).join('')}
                </div>
            ` : ''}
        </div>
    `).join('');
}
