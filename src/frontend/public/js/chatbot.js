const OPENAI_API_URL = 'http://localhost:5100/api/chat';

async function sendMessageToAssistant(message) {
    try {
        const response = await fetch(OPENAI_API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                prompt: message
            })
        });

        if (!response.ok) {
            throw new Error('Error en la respuesta del servidor');
        }

        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }

        return data.response;
    } catch (error) {
        console.error('Error al enviar mensaje:', error);
        throw error;
    }
}

function displayMessage(message, isUser = false) {
    const messageElement = document.createElement('div');
    messageElement.classList.add('mb-2', 'p-2', 'rounded');
    
    if (isUser) {
        messageElement.classList.add('bg-green-50');
    } else {
        messageElement.classList.add('bg-gray-50');
    }
    
    messageElement.innerHTML = `
        <p class="text-xs text-gray-500 font-semibold">${isUser ? 'Tú' : 'Asistente'}:</p>
        <p class="text-sm whitespace-pre-wrap">${message}</p>
    `;
    
    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    return messageElement;
}