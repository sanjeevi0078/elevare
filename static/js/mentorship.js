/**
 * Mentorship Page Integration
 * Real-time AI Mentor RAG chatbot
 */

let chatHistory = [];

document.addEventListener('DOMContentLoaded', async () => {
    console.log('✅ Mentorship page loaded');
    
    // Initialize chat
    await initializeChat();
    
    // Load mentor topics
    await loadMentorTopics();
    
    // Setup event listeners
    setupEventListeners();
});

/**
 * Initialize the AI Mentor chat interface
 */
async function initializeChat() {
    try {
        const status = await api.getMentorStatus();
        console.log('✅ AI Mentor online:', status);
        
        // Add welcome message
        addChatMessage({
            type: 'system',
            message: `👋 Welcome! I'm your AI startup mentor. I have access to knowledge on ${status.knowledge_base?.documents || 5} key topics: Product-Market Fit, Fundraising, Team Building, Legal Compliance, and Go-to-Market strategies. Ask me anything!`,
            timestamp: new Date().toISOString()
        });
    } catch (error) {
        console.error('Error initializing chat:', error);
        addChatMessage({
            type: 'error',
            message: '❌ AI Mentor is currently unavailable. Please try again later.',
            timestamp: new Date().toISOString()
        });
    }
}

/**
 * Load available mentor topics
 */
async function loadMentorTopics() {
    const topicsContainer = document.getElementById('mentor-topics');
    if (!topicsContainer) return;

    try {
        const data = await api.getMentorTopics();
        
        if (data.topics && data.topics.length > 0) {
            topicsContainer.innerHTML = data.topics.map(topic => `
                <div class="bg-black/30 rounded-lg border border-gray-800 p-4 hover:border-indigo-500 transition cursor-pointer"
                     onclick="askExampleQuestion('${topic.example_question.replace(/'/g, "\\'")}')">
                    <h5 class="font-semibold text-indigo-400 mb-2">
                        <i class="fas fa-lightbulb"></i> ${topic.name}
                    </h5>
                    <p class="text-sm text-gray-400 mb-2">${topic.description}</p>
                    <p class="text-xs text-gray-500 italic">
                        Example: "${topic.example_question}"
                    </p>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading topics:', error);
    }
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    
    if (chatInput && sendButton) {
        sendButton.addEventListener('click', sendMessage);
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }
}

/**
 * Send a message to the AI Mentor
 */
async function sendMessage() {
    const chatInput = document.getElementById('chat-input');
    const question = chatInput?.value.trim();
    
    if (!question || question.length < 10) {
        alert('Please enter a question (at least 10 characters)');
        return;
    }
    
    // Clear input
    chatInput.value = '';
    
    // Add user message to chat
    addChatMessage({
        type: 'user',
        message: question,
        timestamp: new Date().toISOString()
    });
    
    // Show typing indicator
    const typingId = addTypingIndicator();
    
    try {
        // Call AI Mentor API
        const response = await api.askMentor(question);
        
        // Remove typing indicator
        removeTypingIndicator(typingId);
        
        // Add AI response
        addChatMessage({
            type: 'ai',
            message: response.answer,
            sources: response.sources,
            timestamp: new Date().toISOString()
        });
        
    } catch (error) {
        console.error('Error asking mentor:', error);
        removeTypingIndicator(typingId);
        
        addChatMessage({
            type: 'error',
            message: `❌ Sorry, I encountered an error: ${error.message}. Please try again.`,
            timestamp: new Date().toISOString()
        });
    }
}

/**
 * Add a message to the chat display
 */
function addChatMessage(message) {
    chatHistory.push(message);
    
    const chatMessages = document.getElementById('chat-messages');
    if (!chatMessages) return;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${message.type}`;
    
    const time = new Date(message.timestamp).toLocaleTimeString([], { 
        hour: '2-digit', 
        minute: '2-digit' 
    });
    
    if (message.type === 'user') {
        messageDiv.innerHTML = `
            <div class="flex justify-end mb-4">
                <div class="bg-indigo-600 rounded-lg rounded-tr-none px-4 py-3 max-w-2xl">
                    <p class="text-white">${escapeHtml(message.message)}</p>
                    <p class="text-xs text-indigo-200 mt-1">${time}</p>
                </div>
            </div>
        `;
    } else if (message.type === 'ai') {
        messageDiv.innerHTML = `
            <div class="flex justify-start mb-4">
                <div class="bg-gray-800 rounded-lg rounded-tl-none px-4 py-3 max-w-2xl">
                    <div class="flex items-center gap-2 mb-2">
                        <span class="text-2xl">🤖</span>
                        <span class="text-sm font-semibold text-green-400">AI Mentor</span>
                    </div>
                    <p class="text-white whitespace-pre-wrap">${escapeHtml(message.message)}</p>
                    ${message.sources ? `
                        <div class="mt-3 pt-3 border-t border-gray-700">
                            <p class="text-xs text-gray-400">
                                <i class="fas fa-book"></i> Sources: ${escapeHtml(message.sources.substring(0, 100))}...
                            </p>
                        </div>
                    ` : ''}
                    <p class="text-xs text-gray-500 mt-2">${time}</p>
                </div>
            </div>
        `;
    } else if (message.type === 'system') {
        messageDiv.innerHTML = `
            <div class="flex justify-center mb-4">
                <div class="bg-blue-900/30 rounded-lg px-4 py-2 text-sm text-blue-200">
                    ${escapeHtml(message.message)}
                </div>
            </div>
        `;
    } else if (message.type === 'error') {
        messageDiv.innerHTML = `
            <div class="flex justify-center mb-4">
                <div class="bg-red-900/30 rounded-lg px-4 py-2 text-sm text-red-200">
                    ${escapeHtml(message.message)}
                </div>
            </div>
        `;
    }
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * Add typing indicator
 */
function addTypingIndicator() {
    const chatMessages = document.getElementById('chat-messages');
    if (!chatMessages) return null;
    
    const typingDiv = document.createElement('div');
    typingDiv.id = 'typing-indicator';
    typingDiv.className = 'flex justify-start mb-4';
    typingDiv.innerHTML = `
        <div class="bg-gray-800 rounded-lg rounded-tl-none px-4 py-3">
            <div class="flex items-center gap-2">
                <span class="text-2xl">🤖</span>
                <span class="text-sm text-gray-400">AI Mentor is thinking</span>
                <div class="flex gap-1">
                    <div class="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
                    <div class="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style="animation-delay: 150ms"></div>
                    <div class="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style="animation-delay: 300ms"></div>
                </div>
            </div>
        </div>
    `;
    
    chatMessages.appendChild(typingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    return 'typing-indicator';
}

/**
 * Remove typing indicator
 */
function removeTypingIndicator(id) {
    const indicator = document.getElementById(id);
    if (indicator) {
        indicator.remove();
    }
}

/**
 * Ask an example question
 */
function askExampleQuestion(question) {
    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.value = question;
        chatInput.focus();
    }
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Make functions global
window.sendMessage = sendMessage;
window.askExampleQuestion = askExampleQuestion;
