import os
import json
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

nebius_api_key = os.getenv("NEBIUS_API_KEY")
client = AsyncOpenAI(
    base_url="https://api.tokenfactory.nebius.com/v1/",
    api_key=nebius_api_key
)

async def generate_synthetic_market_tape(scenario_prompt: str) -> list:
    """Uses Llama 3.1 70B to generate the synthetic market tape."""
    prompt = (
        f"You are a quantitative trading market simulator. Generate a synthetic market tape based on the following scenario: {scenario_prompt}\n"
        "Return ONLY a JSON array of objects, where each object has the keys: time, event, price, volume. Do not include markdown blocks or any other text."
    )
    
    response = await client.chat.completions.create(
        model="deepseek-ai/DeepSeek-V4-Pro",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    
    content = response.choices[0].message.content.strip()
    # Strip markdown if present
    if content.startswith("```json"):
        content = content[7:-3].strip()
    elif content.startswith("```"):
        content = content[3:-3].strip()
        
    try:
        data = json.loads(content)
        if isinstance(data, dict) and "tape" in data:
            return data["tape"]
        return data
    except Exception as e:
        print(f"Error parsing tape: {e}, content: {content}")
        return [{"time": "00:00", "event": "Error generating tape", "price": 0, "volume": 0}]

async def audit_code_and_generate_diff(code: str, tape: list) -> dict:
    """Uses Qwen 2.5 Coder 32B to audit the code and generate a diff."""
    tape_str = json.dumps(tape)
    prompt = (
        f"Audit the following trading strategy code against this market tape:\nCode:\n{code}\n\nTape:\n{tape_str}\n\n"
        "Return ONLY a JSON object with the following exact keys:\n"
        "- strategy_verdict (string, e.g. PASS, FAIL, WARNING)\n"
        "- risk_score (integer 0-100)\n"
        "- failure_point (string or null)\n"
        "- vulnerabilities (list of strings)\n"
        "- refactored_code (string)\n"
        "- diff (string)\n"
        "- benchmark_stats (object with dummy stats like max_drawdown, sharpe_ratio)\n\n"
        "Do not include markdown blocks or any other text."
    )
    
    response = await client.chat.completions.create(
        model="deepseek-ai/DeepSeek-V4-Pro",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    
    content = response.choices[0].message.content.strip()
    if content.startswith("```json"):
        content = content[7:-3].strip()
    elif content.startswith("```"):
        content = content[3:-3].strip()
        
    try:
        return json.loads(content)
    except Exception as e:
        print(f"Error parsing audit: {e}, content: {content}")
        return {
            "strategy_verdict": "ERROR",
            "risk_score": 100,
            "failure_point": "JSON parsing error from LLM",
            "vulnerabilities": ["Failed to audit code properly."],
            "refactored_code": code,
            "diff": "",
            "benchmark_stats": {}
        }
