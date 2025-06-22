# services/ai_service.py
import httpx
from config.settings import settings
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY # Or your preferred LLM API key
        self.api_url = "https://api.openai.com/v1/chat/completions" # Example for OpenAI API

    async def analyze_channel_data(self, channel_data: Dict[str, Any]) -> str:
        """
        Performs AI-analysis on channel data and generates a plan.
        `channel_data` would typically include:
        - channel_id, title, username
        - current subscribers count
        - (Conceptual) recent message texts (requires fetching older messages with Telegram API, which can be limited)
        - (Conceptual) engagement metrics (views, forwards per post)
        - etc.
        """
        if not self.api_key:
            logger.warning("AI_SERVICE: No OpenAI API key configured. Returning dummy analysis.")
            return "AI Analysis: Limited functionality without API key. Your channel has good vibes! Focus on consistency."

        prompt = f"""
        Analyze the following Telegram channel data and provide a concise, actionable growth and sales plan.
        The analysis should be comprehensive but presented in a user-friendly way.
        Channel title: {channel_data.get('title', 'N/A')}
        Channel username: @{channel_data.get('username', 'N/A')}
        Current subscribers: {channel_data.get('subscribers_count', 'N/A')}
        Recent message engagement (conceptual values for example): Average engagement, some fluctuation in views.

        Provide:
        1. A brief summary of the channel's current status (e.g., "The channel shows consistent growth, but engagement could be improved.").
        2. Key strengths and weaknesses based on the data.
        3. 3-5 actionable recommendations for organic growth (e.g., "Post regularly, use polls, engage with comments.").
        4. 2-3 actionable recommendations for monetization/sales (e.g., "Offer sponsored posts, sell digital products.").
        5. A concluding remark encouraging the user.
        Format as plain text, using newlines for separation, and bold text for titles like **Summary**, **Strengths**, etc. Use bullet points for recommendations. Do not use Markdown headers other than bold.
        """

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        body = {
            "model": "gpt-3.5-turbo", # Or gpt-4, etc.
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 700, # Increased for more detailed response
            "temperature": 0.7
        }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(self.api_url, headers=headers, json=body)
                response.raise_for_status()
                response_data = response.json()
                analysis = response_data['choices'][0]['message']['content']
                logger.info(f"AI analysis generated for channel {channel_data.get('title')}.")
                return analysis
        except httpx.HTTPStatusError as e:
            logger.error(f"AI service HTTP error: {e.response.status_code} - {e.response.text} for channel {channel_data.get('title')}", exc_info=True)
            return "Failed to get AI analysis due to API error. Please try again later."
        except Exception as e:
            logger.error(f"AI service unexpected error for channel {channel_data.get('title')}: {e}", exc_info=True)
            return "Failed to get AI analysis due to an internal error. Please try again later."