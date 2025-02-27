// script.js
document.addEventListener('DOMContentLoaded', () => {
    const messageContainer = document.getElementById('chatbot-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-btn');
  
    // Function to add a message to the chat
    function addMessage(text, isUser) {
      const messageDiv = document.createElement('div');
      messageDiv.classList.add('message', isUser ? 'user' : 'bot');
      const messageText = document.createElement('p');
      messageText.textContent = text;
      messageDiv.appendChild(messageText);
      messageContainer.appendChild(messageDiv);
      messageContainer.scrollTop = messageContainer.scrollHeight; // Auto-scroll
    }
  
    // Function to handle user input
    function handleUserInput() {
      const userText = userInput.value.trim();
      if (userText) {
        addMessage(userText, true); // Add user message
        userInput.value = ''; // Clear input field
  
        // Simulate bot response (replace with actual API call)
        fetch('/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ message: userText })
        })
        .then(response => response.json())
        .then(data => {
          addMessage(data.response, false); // Add bot message
        })
        .catch(error => {
          console.error('Error:', error);
          addMessage('Sorry, there was an error processing your request.', false); // Add error message
        });

        // addMessage(data.response, false);

      }
    }
  
    // Event listeners
    sendButton.addEventListener('click', handleUserInput);
    userInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        handleUserInput();
      }
    });
  });