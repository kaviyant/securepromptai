from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from app.schemas.pydantic_schemas import LLMProxyRequest
from app.api.dependencies import get_current_employee
from app.config.settings import settings
from app.services.groq_service import GroqService
from engine.firewall import PromptFirewall
from typing import Dict, Any, Optional
import json

router = APIRouter(tags=["LLM Proxy Services"])
firewall = PromptFirewall()
groq_service = GroqService()

@router.post("/api/groq", response_model=Dict[str, Any])
async def proxy_groq_request(
    request: LLMProxyRequest,
    current_user: Dict[str, Any] = Depends(get_current_employee)
):
    """
    Validates user prompts for security violations using PromptFirewall. 
    If compliant, submits ONLY the sanitized prompt to the Groq API.
    Gated by Employee role access.
    """
    department = current_user.get("department", "General Operations")
    
    # 1. Run prompt through firewall decision engine
    firewall_result = firewall.scan_and_decide(
        prompt_text=request.prompt,
        department=department,
        auto_sanitize_pii=True # Always sanitize PII for outbound LLM proxying
    )

    # Record scan to Prometheus
    from app.middleware.prometheus import PrometheusMetrics
    PrometheusMetrics.record_scan(
        action=firewall_result["action"],
        risk_level=firewall_result["risk_level"],
        model="PromptFirewall"
    )

    if firewall_result["action"] == "BLOCK":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Prompt submission blocked due to security policy violations.",
                "explanation": firewall_result["explanation"],
                "risk_score": firewall_result["risk_score"],
                "risk_level": firewall_result["risk_level"]
            }
        )

    # 2. Get sanitized prompt
    sanitized_prompt = firewall_result["sanitized_prompt"]

    # In sandbox or offline testing, check if API key is mock
    if "mock" in settings.GROQ_API_KEY or not settings.GROQ_API_KEY:
        return {
            "model": request.model,
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": f"[SANDBOX MOCK RESPONSE] Prompt passed firewall checks! Sanitized text sent to LLM: '{sanitized_prompt}'"
                    },
                    "finish_reason": "stop"
                }
            ],
            "security_verified": True,
            "sanitized": firewall_result["action"] == "SANITIZE"
        }

    # 3. Call Groq Service (with built-in retries, timeouts, and rate limits)
    try:
        messages = [{"role": "user", "content": sanitized_prompt}]
        response = await groq_service.complete_chat(
            messages=messages,
            model=request.model,
        )
        # Append security audit attributes
        response["security_verified"] = True
        response["sanitized"] = firewall_result["action"] == "SANITIZE"
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to communicate with Groq API gateway: {str(e)}"
        )

@router.post("/api/groq/stream")
async def proxy_groq_stream(
    request: LLMProxyRequest,
    current_user: Dict[str, Any] = Depends(get_current_employee)
):
    """
    Streams LLM completions back to the client using Server-Sent Events (SSE)
    after verifying and sanitizing prompts via PromptFirewall.
    """
    department = current_user.get("department", "General Operations")
    
    # 1. Firewall Security Scan
    firewall_result = firewall.scan_and_decide(
        prompt_text=request.prompt,
        department=department,
        auto_sanitize_pii=True
    )

    # Record scan to Prometheus
    from app.middleware.prometheus import PrometheusMetrics
    PrometheusMetrics.record_scan(
        action=firewall_result["action"],
        risk_level=firewall_result["risk_level"],
        model="PromptFirewall"
    )

    if firewall_result["action"] == "BLOCK":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Prompt blocked by security firewall.",
                "explanation": firewall_result["explanation"]
            }
        )

    # In offline sandbox check
    if "mock" in settings.GROQ_API_KEY or not settings.GROQ_API_KEY:
        async def mock_generator():
            yield "data: " + json.dumps({"choices": [{"delta": {"content": "[SANDBOX STREAMING MOCK] "}}]}) + "\n\n"
            words = f"Prompt checked and verified! Sanitized prompt: '{firewall_result['sanitized_prompt']}'".split()
            for w in words:
                yield "data: " + json.dumps({"choices": [{"delta": {"content": w + " "}}]}) + "\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(mock_generator(), media_type="text/event-stream")

    # 2. Return SSE Stream Response
    async def event_generator():
        messages = [{"role": "user", "content": firewall_result["sanitized_prompt"]}]
        async for chunk in groq_service.stream_chat(messages=messages, model=request.model):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
