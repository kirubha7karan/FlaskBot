// script.js
document.addEventListener('DOMContentLoaded', () => {
  const messageContainer = document.getElementById('chatbot-messages');
  const userInput = document.getElementById('user-input');
  const sendButton = document.getElementById('send-btn');

  // Function to add a message to the chat
  function addMessage(text, isUser, isLoader = false) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', isUser ? 'user' : 'bot');

    if (isLoader) {
      // Add loader inside the bot's message
      const loaderDiv = document.createElement('div');
      loaderDiv.classList.add('loader');
      messageDiv.appendChild(loaderDiv);
    } else {
      // Add regular message text
      const messageText = document.createElement('p');
      messageText.textContent = text;
      if (!isUser) {
        messageText.innerHTML = marked.parse(text);
      } else {
        messageText.textContent = text;
      }
      messageDiv.appendChild(messageText);
    }

    messageContainer.appendChild(messageDiv);
    messageContainer.scrollTop = messageContainer.scrollHeight; // Auto-scroll
  }

  // Function to simulate a bot response (replace with actual API call)
  function simulateBotResponse(userText) {
    return new Promise((resolve) => {
    
    fetch("/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message: userText }),
    })
      .then((response) => response.json())
      .then((data) => {

        resolve(data.response);
      })
      .catch((error) => {
        console.error("Error:", error);
        resolve("Sorry, there was an error processing your request.");
      });
    });
  }

  // Function to handle user input
  async function handleUserInput() {
    const userText = userInput.value.trim();
    if (userText) {
      addMessage(userText, true); // Add user message
      userInput.value = ''; // Clear input field
      userInput.disabled = true;

      // Add loader as bot's message
      addMessage('', false, true);

      const botResponse = await simulateBotResponse(userText);

      // Remove the loader and add the bot's response
      messageContainer.lastChild.remove(); // Remove loader
      addMessage(botResponse, false); // Add bot response
      userInput.disabled = false;
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