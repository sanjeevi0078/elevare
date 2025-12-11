/**
 * Event Scout - AI-Powered Event Discovery
 * Finds personalized startup events using live web search
 */

document.addEventListener('DOMContentLoaded', () => {
    console.log('🎯 Event Scout: Initializing...');
    
    // Check if we have user preferences saved, otherwise use defaults
    const userInterest = localStorage.getItem('user_interest') || 'Technology';
    const userLocation = localStorage.getItem('user_location') || 'San Francisco';
    const userStage = localStorage.getItem('user_stage') || 'early';
    
    console.log(`📊 User Profile: ${userInterest} in ${userLocation} (${userStage} stage)`);
    
    loadRealEvents(userInterest, userLocation, userStage);
});

/**
 * Fetch events from the Event Scout API
 */
async function loadRealEvents(interest, location, stage) {
    const container = document.getElementById('events-grid');
    
    if (!container) {
        console.error('❌ Events grid container not found!');
        return;
    }
    
    // Show Loading Skeleton
    container.innerHTML = `
        <div class="col-span-full text-center py-16">
            <div class="inline-block animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-purple-500 mb-4"></div>
            <p class="text-purple-300 text-lg font-semibold animate-pulse">
                🤖 Running AI Event Scout for ${interest} in ${location}...
            </p>
            <p class="text-gray-400 text-sm mt-2">Searching the web for upcoming events</p>
        </div>
    `;

    try {
        console.log('🚀 Fetching events from API...');
        
        const response = await fetch('/events/discover', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            },
            body: JSON.stringify({ 
                interest: interest, 
                location: location, 
                stage: stage 
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to fetch events');
        }
        
        const data = await response.json();
        console.log('✅ Events received:', data.events.length, data);
        
        renderEvents(data.events);
        
    } catch (error) {
        console.error('❌ Event loading failed:', error);
        container.innerHTML = `
            <div class="col-span-full text-center py-16">
                <div class="text-6xl mb-4">😕</div>
                <p class="text-red-400 text-lg font-semibold mb-2">Failed to load events</p>
                <p class="text-gray-400 text-sm">${error.message}</p>
                <button onclick="location.reload()" class="mt-6 px-6 py-3 bg-purple-600 hover:bg-purple-700 rounded-lg font-semibold transition-colors">
                    Try Again
                </button>
            </div>
        `;
    }
}

/**
 * Render event cards to the DOM
 */
function renderEvents(events) {
    const container = document.getElementById('events-grid');
    
    if (!events || events.length === 0) {
        container.innerHTML = `
            <div class="col-span-full text-center py-16">
                <div class="text-6xl mb-4">📅</div>
                <h3 class="text-2xl font-bold text-gray-300 mb-2">No Events Found</h3>
                <p class="text-gray-400">Try adjusting your preferences or check back later</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = ''; // Clear loading state
    
    events.forEach((event, index) => {
        const badgeColor = getCategoryColor(event.category);
        
        const cardHtml = `
        <div class="relative bg-gray-900/80 border border-gray-700 rounded-2xl overflow-hidden hover:border-purple-500 transition-all hover:transform hover:-translate-y-1 shadow-lg group animate-fade-in" style="animation-delay: ${index * 0.1}s">
            
            ${event.tag ? `
                <div class="absolute top-4 right-4 bg-yellow-500/20 text-yellow-300 text-xs font-bold px-3 py-1 rounded-full border border-yellow-500/50 flex items-center gap-1">
                    <i class="fas fa-crown"></i> ${event.tag}
                </div>
            ` : ''}
            
            <div class="p-6">
                <div class="flex justify-between items-start mb-4">
                    <span class="${badgeColor} text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wide">
                        ${event.category}
                    </span>
                    <span class="text-gray-400 text-sm flex items-center gap-1">
                        <i class="fas fa-calendar"></i> ${event.date}
                    </span>
                </div>
                
                <h3 class="text-xl font-bold text-white mb-2 group-hover:text-purple-300 transition-colors">
                    ${event.title}
                </h3>
                <p class="text-gray-400 text-sm mb-4 line-clamp-2">${event.description}</p>
                
                <div class="flex items-center justify-between border-t border-gray-800 pt-4 mt-4">
                    <div class="flex flex-col">
                        <span class="text-xs text-gray-500">Location</span>
                        <span class="text-sm text-gray-300">
                            <i class="fas fa-map-marker-alt text-purple-500 mr-1"></i> ${event.location}
                        </span>
                    </div>
                    <div class="flex flex-col text-right">
                        <span class="text-xs text-gray-500">Entry</span>
                        <span class="text-sm font-bold ${event.price === 'Free' ? 'text-green-400' : 'text-blue-400'}">
                            ${event.price}
                        </span>
                    </div>
                </div>
                
                <a href="${event.url}" target="_blank" rel="noopener noreferrer" 
                   class="block w-full mt-4 text-center bg-purple-600/20 hover:bg-purple-600 text-purple-300 hover:text-white font-bold py-3 rounded-lg transition-all border border-purple-600/50">
                    <i class="fas fa-external-link-alt mr-2"></i>Register Now
                </a>
            </div>
        </div>
        `;
        
        container.innerHTML += cardHtml;
    });
    
    console.log(`✅ Rendered ${events.length} event cards`);
}

/**
 * Get color scheme based on event category
 */
function getCategoryColor(category) {
    const colorMap = {
        'Conference': 'bg-blue-500/20 text-blue-300 border border-blue-500/30',
        'Pitch': 'bg-pink-500/20 text-pink-300 border border-pink-500/30',
        'Networking': 'bg-green-500/20 text-green-300 border border-green-500/30',
        'Workshop': 'bg-orange-500/20 text-orange-300 border border-orange-500/30'
    };
    
    return colorMap[category] || 'bg-purple-500/20 text-purple-300 border border-purple-500/30';
}

// Add CSS animation for fade-in effect
const style = document.createElement('style');
style.textContent = `
    @keyframes fade-in {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    .animate-fade-in {
        animation: fade-in 0.5s ease-out forwards;
        opacity: 0;
    }
`;
document.head.appendChild(style);
