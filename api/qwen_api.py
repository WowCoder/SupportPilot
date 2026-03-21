import requests
import logging
from flask import current_app

logger = logging.getLogger(__name__)


class QwenAPI:
    def __init__(self):
        self.api_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        self.default_model = "qwen-turbo"
        self.timeout = 30  # Request timeout in seconds

    def _get_api_key(self):
        """Get API key from current app config"""
        try:
            return current_app.config.get('QWEN_API_KEY')
        except RuntimeError:
            # Outside of app context, use environment variable
            import os
            return os.environ.get('QWEN_API_KEY')

    def generate_response(self, query, context=None):
        """
        Generate response using Alibaba Qwen API with context

        Args:
            query: User query
            context: List of relevant context strings

        Returns:
            AI-generated response string
        """
        api_key = self._get_api_key()
        if not api_key:
            logger.error('QWEN_API_KEY is not configured')
            return "抱歉，API 密钥未配置，无法生成回复。"

        # Build prompt with context
        if context:
            if isinstance(context, list):
                # Handle new format with similarity scores
                if context and isinstance(context[0], dict):
                    context_str = "\n".join([
                        f"相关知识：{item['content']} (相似度：{item['similarity']:.2f})"
                        for item in context if item.get('similarity', 0) > 0.1
                    ])
                else:
                    context_str = "\n".join([f"相关知识：{item}" for item in context])
            else:
                context_str = f"相关知识：{context}"
            message = f"{context_str}\n\n用户问题：{query}"
        else:
            message = query

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        data = {
            "model": self.default_model,
            "messages": [
                {"role": "system", "content": "你是一个 helpful 的客户支持助手。使用提供的知识来回答用户问题。如果知识库中没有相关信息，请诚实地告诉用户。"},
                {"role": "user", "content": message}
            ],
            "temperature": 0.7,
            "max_tokens": 1024
        }

        try:
            logger.debug(f'Sending request to Qwen API with query: {query[:100]}...')
            response = requests.post(
                self.api_url,
                headers=headers,
                json=data,
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()

            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                logger.debug(f'Received response from Qwen API')
                return content
            else:
                logger.warning(f'Unexpected API response format: {result}')
                return "抱歉，无法解析 AI 回复，请稍后重试。"

        except requests.exceptions.Timeout:
            logger.error('Qwen API request timeout')
            return "抱歉，AI 服务响应超时，请稍后重试。"

        except requests.exceptions.ConnectionError as e:
            logger.error(f'Qwen API connection error: {e}')
            return "抱歉，无法连接到 AI 服务，请检查网络连接。"

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else 'unknown'
            logger.error(f'Qwen API HTTP error {status_code}: {e}')
            if status_code == 401:
                return "抱歉，API 密钥验证失败。"
            elif status_code == 429:
                return "抱歉，API 请求过于频繁，请稍后重试。"
            else:
                return f"抱歉，AI 服务返回错误（状态码：{status_code}）。"

        except requests.exceptions.RequestException as e:
            logger.error(f'Qwen API request error: {e}', exc_info=True)
            return "抱歉，AI 服务请求失败，请稍后重试。"

        except Exception as e:
            logger.error(f'Unexpected error generating response: {e}', exc_info=True)
            return "抱歉，发生未知错误，请稍后重试。"


qwen_api = QwenAPI()
