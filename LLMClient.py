import logging
import openai
from typing import List, Dict, Optional, Iterator

logger = logging.getLogger(__name__)


class LLMClient:
    """
    OpenAI API compatible client class
    """

    def __init__(self, base_url: str, api_key: str, model: str):
        """
        Initialize OpenAI API client
        :param base_url: Base URL for OpenAI API
        :param api_key: OpenAI API key
        :param model: Name of the model to use
        """
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.client = openai.OpenAI(
            base_url=base_url,
            api_key=api_key
        )

    def completion(
            self,
            user_message: str,
            system_prompt: Optional[str] = None,
            image_paths: Optional[List[str]] = None,
            temperature: float = 0.7,
            max_tokens: int = 8192
    ) -> Iterator[str]:
        """
        Create chat dialogue with streaming response.
        
        Args:
            user_message: User message content
            system_prompt: System prompt (optional)
            image_paths: List of image paths (optional) - currently not used with streaming
            temperature: Generation temperature
            max_tokens: Maximum number of tokens
            
        Returns:
            Iterator[str]: An iterator yielding chunks of the model generated response content.
        """
        # 构造消息内容
        user_content = [{"type": "text", "text": user_message}]
        if system_prompt:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
        else:
            messages = [
                {"role": "user", "content": user_content}
            ]
        
        # 注意：当前实现未包含处理 image_paths 的流式逻辑
        if image_paths:
             logger.warning("Image paths provided but streaming currently only supports text.")
             # 如果需要支持图像，需要调整消息构造方式，类似非流式但需确认 API 支持

        try:
            stream = None
            request_params = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True # 启用流式响应
            }

            if "openrouter.ai" in str(self.base_url).lower():
                request_params["extra_headers"] = {
                        "X-Title": "NPY Translator", # 更新应用名称
                        "HTTP-Referer": "https://github.com/your_repo", # 如果有仓库，更新链接
                    }
                stream = self.client.chat.completions.create(**request_params)
            else:
                stream = self.client.chat.completions.create(**request_params)
            
            # 迭代处理流式响应
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content # yield 内容块

        except Exception as e:
            logger.error(f"API stream request failed: {str(e)}")
            # 在流式传输中，错误可能在迭代期间发生
            # 可以选择 yield 一个错误标记或者直接 raise
            yield f"\n[错误：API 请求失败: {str(e)}]" # 或者 raise e，让调用方处理
            # raise e # 取消注释以向上抛出异常

    def encode_image(self, image_path: str) -> str:
        import base64
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
