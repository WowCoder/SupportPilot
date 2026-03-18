import requests
from app import app

class QwenAPI:
    def __init__(self):
        self.api_key = app.config['QWEN_API_KEY']
        self.api_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    
    def generate_response(self, query, context=[]):
        """Generate response using Alibaba Qwen API with context"""
        # Build prompt with context
        if context:
            context_str = "\n".join([f"Knowledge: {item}" for item in context])
            message = f"{context_str}\n\n{query}"
        else:
            message = query
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            data = {
                "model": "qwen-turbo",  # This model has free tier
                "messages": [
                    {"role": "system", "content": "你是一个 helpful 的客户支持助手。使用提供的知识来回答用户问题。"},
                    {"role": "user", "content": message}
                ],
                "temperature": 0.7
            }
            response = requests.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            return f"Error generating response: {str(e)}"

qwen_api = QwenAPI()