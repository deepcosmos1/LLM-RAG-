const chatbotIcon = document.getElementById('chatbot-icon');
const closeChatbot = document.getElementById('close-chatbot');
const chatbotContainer = document.getElementById('chatbot-container');
const chatbotMessages = document.getElementById('chatbot-messages');
const userInput = document.getElementById('user-input');
const sendMessage = document.getElementById('send-message');


const socket = io('http://localhost:5000', { // Replace with your server URL
    transports: ['websocket'],
    reconnection: true,
    reconnectionAttempts: 5,
    reconnectionDelay: 1000,
    timeout: 10000
});


let userId = null;

socket.on('connect', () => {
    console.log('Connected to server');
});

socket.on('connect_error', (error) => {
    console.error('Connection error:', error);
});

socket.on('set_user_id', (data) => {
    userId = data.user_id;
    console.log('Received user ID:', userId);
    socket.emit('join', { user_id: userId });
});

socket.on('bot_response', (message) => {
    addMessage(message.data, 'bot-message');
});

chatbotIcon.addEventListener('click', () => {
    chatbotContainer.style.display = 'flex';
    chatbotIcon.style.display = 'none';
});

closeChatbot.addEventListener('click', () => {
    chatbotContainer.style.display = 'none';
    chatbotIcon.style.display = 'flex';
});

sendMessage.addEventListener('click', sendUserMessage);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendUserMessage();
    }
});

function sendUserMessage() {
    const message = userInput.value.trim();
    if (message && userId) {
        addMessage(message, 'user-message');
        userInput.value = '';
        socket.emit('user_message', { data: message, user_id: userId });
    }
}

function addMessage(message, className) {
    const messageElement = document.createElement('div');
    messageElement.classList.add('message', className);
    messageElement.textContent = message;
    chatbotMessages.appendChild(messageElement);
    chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
}