from dotenv import load_dotenv
from groq import Groq
import os

load_dotenv()

class GroqLLM:
    def __init__(self, api_key=None, model="llama-3.3-70b-versatile"):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.model = model
        self.client = Groq(api_key=self.api_key)
    
    async def agenerate(self, *, chat_ctx, **kwargs):
        # Convert chat context to messages format
        messages = []
        for msg in chat_ctx.messages:
            if hasattr(msg, 'role') and hasattr(msg, 'content'):
                # Handle different content types
                content = ""
                if isinstance(msg.content, list):
                    for item in msg.content:
                        if hasattr(item, 'text'):
                            content += item.text
                        elif isinstance(item, str):
                            content += item
                else:
                    content = str(msg.content)
                
                messages.append({
                    "role": msg.role,
                    "content": content
                })
        
        # Add system message if not present
        if not messages or messages[0]["role"] != "system":
            messages.insert(0, {
                "role": "system", 
                "content": "You are a funny, witty assistant. Respond with short and concise answers. Avoid using unpronounceable punctuation or emojis."
            })
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.1,
            max_tokens=256
        )
        
        # Return the response in the expected format
        return response.choices[0].message.content