# src/api/deepseek_client.py
import os
import json
import asyncio
from typing import Dict, List, Optional, Any, AsyncGenerator
import aiohttp
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import logging

# 配置日志
logger = logging.getLogger(__name__)

class ModelType(Enum):
    """支持的模型类型"""
    DEEPSEEK_CHAT = "deepseek-chat"
    DEEPSEEK_CODER = "deepseek-coder"

@dataclass
class DeepSeekConfig:
    """DeepSeek配置类"""
    api_key: str
    base_url: str = "https://api.deepseek.com"
    default_model: ModelType = ModelType.DEEPSEEK_CHAT
    timeout: int = 60
    max_retries: int = 3
    temperature: float = 0.3
    max_tokens: int = 2000

class DeepSeekError(Exception):
    """DeepSeek API异常"""
    pass

class RateLimitError(DeepSeekError):
    """速率限制异常"""
    pass

class AuthenticationError(DeepSeekError):
    """认证异常"""
    pass

class DeepSeekClient:
    """DeepSeek API客户端"""
    
    def __init__(self, config: DeepSeekConfig):
        self.config = config
        self.session = None
        self._setup_logging()
        
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
    
    async def connect(self):
        """创建会话连接"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers=self._get_headers()
            )
    
    async def close(self):
        """关闭会话"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[ModelType] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """聊天补全接口"""
        
        model = model or self.config.default_model
        temperature = temperature or self.config.temperature
        max_tokens = max_tokens or self.config.max_tokens
        
        payload = {
            "model": model.value,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }
        
        for retry in range(self.config.max_retries):
            try:
                logger.info(f"发送请求到DeepSeek API，重试次数: {retry}")
                
                async with self.session.post(
                    f"{self.config.base_url}/chat/completions",
                    json=payload
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"API响应成功，token使用: {data.get('usage', {})}")
                        return data
                    
                    elif response.status == 429:
                        wait_time = 2 ** retry  # 指数退避
                        logger.warning(f"速率限制，等待 {wait_time} 秒后重试")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    elif response.status == 401:
                        raise AuthenticationError("API密钥无效或过期")
                    
                    elif response.status == 403:
                        raise AuthenticationError("没有访问权限")
                    
                    else:
                        error_text = await response.text()
                        logger.error(f"API请求失败: {response.status}, {error_text}")
                        raise DeepSeekError(f"API错误: {response.status}")
                        
            except aiohttp.ClientError as e:
                logger.error(f"网络错误: {str(e)}")
                if retry == self.config.max_retries - 1:
                    raise DeepSeekError(f"网络错误: {str(e)}")
                await asyncio.sleep(1)
        
        raise DeepSeekError("超过最大重试次数")
    
    async def batch_chat_completion(
        self,
        prompts: List[str],
        system_prompt: str = None,
        model: Optional[ModelType] = None,
        max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """批量聊天补全"""
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_prompt(prompt: str) -> Dict[str, Any]:
            async with semaphore:
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                return await self.chat_completion(messages, model=model)
        
        tasks = [process_prompt(prompt) for prompt in prompts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"处理提示 {i} 失败: {str(result)}")
                processed_results.append({
                    "error": str(result),
                    "index": i,
                    "prompt": prompts[i]
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[ModelType] = None,
        temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        """流式聊天补全"""
        
        model = model or self.config.default_model
        temperature = temperature or self.config.temperature
        
        payload = {
            "model": model.value,
            "messages": messages,
            "temperature": temperature,
            "stream": True
        }
        
        try:
            async with self.session.post(
                f"{self.config.base_url}/chat/completions",
                json=payload
            ) as response:
                
                if response.status != 200:
                    raise DeepSeekError(f"API错误: {response.status}")
                
                async for line in response.content:
                    if line:
                        line = line.decode('utf-8').strip()
                        if line.startswith("data: "):
                            data = line[6:]  # 移除"data: "前缀
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                if "choices" in chunk and chunk["choices"]:
                                    delta = chunk["choices"][0].get("delta", {})
                                    if "content" in delta:
                                        yield delta["content"]
                            except json.JSONDecodeError:
                                continue
        
        except aiohttp.ClientError as e:
            logger.error(f"流式请求错误: {str(e)}")
            raise DeepSeekError(f"网络错误: {str(e)}")
    
    def format_prompt_for_test_case(
        self,
        requirement: str,
        domain: str,
        controller: str,
        constraints: List[str],
        standards: List[str]
    ) -> List[Dict[str, str]]:
        """格式化测试用例生成提示词"""
        
        system_prompt = """你是一名专业的汽车测试工程师，具有丰富的HIL测试、实车测试和台架测试经验。
你的任务是生成高质量、可执行的测试用例，必须符合相关标准和规范。"""
        
        user_prompt = f"""请为以下需求生成详细的测试用例：

# 测试需求
{requirement}

# 测试上下文
- 测试领域：{domain}
- 目标控制器：{controller}
- 相关标准：{', '.join(standards) if standards else '无特定标准'}
- 约束条件：
{chr(10).join(f'  - {c}' for c in constraints) if constraints else '  无特定约束'}

# 生成要求
1. 测试用例必须包含以下部分：
   - 前置条件
   - 测试步骤（具体、可执行）
   - 预期结果（量化、可验证）
   - 通过标准

2. 必须考虑：
   - 正常功能验证
   - 边界条件测试
   - 异常情况处理
   - 性能指标验证

3. 格式要求：
   - 使用中文
   - 步骤编号清晰
   - 数据具体化
   - 验证方法明确

请开始生成测试用例："""
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

# 异步上下文管理器使用示例
async def example_usage():
    config = DeepSeekConfig(api_key="your-api-key")
    
    async with DeepSeekClient(config) as client:
        # 单次请求
        messages = [
            {"role": "user", "content": "你好，请帮我生成一个测试用例"}
        ]
        response = await client.chat_completion(messages)
        print(response["choices"][0]["message"]["content"])
        
        # 批量请求
        prompts = ["需求1", "需求2", "需求3"]
        results = await client.batch_chat_completion(prompts)
        for result in results:
            print(result)
        
        # 流式请求
        async for chunk in client.stream_chat_completion(messages):
            print(chunk, end="", flush=True)