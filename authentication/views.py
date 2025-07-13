from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from allauth.socialaccount.models import SocialAccount, SocialToken
from django.conf import settings
import os
import re
import json
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# Helper: validate token (placeholder)
def validate_linkedin_token(token):
    # Implement actual LinkedIn token validation logic here if needed
    # Currently returns True as placeholder
    return True

# Helper: post content to LinkedIn (placeholder)
def post_to_linkedin_api(token, content):
    # Implement actual LinkedIn post logic here using their API
    print(f"Posting to LinkedIn with token: {token} and content: {content}")
    return True

class LinkedInPostView(APIView):
    def post(self, request):
        """
        Receives token + content.
        If token is valid, posts to LinkedIn.
        If missing or invalid, returns login URL for frontend to authenticate first.
        """
        token = request.data.get("token")
        content = request.data.get("content")

        if not token:
            login_url = f"{settings.SITE_URL}/accounts/oidc/<provider_id>/login/"
            return Response({"status": "login_required", "login_url": login_url}, status=401)

        # Validate token
        is_valid = validate_linkedin_token(token)
        if not is_valid:
            login_url = f"{settings.SITE_URL}/accounts/oidc/<provider_id>/login/"
            return Response({"status": "login_required", "login_url": login_url}, status=401)

        # Post to LinkedIn
        success = post_to_linkedin_api(token, content)
        if success:
            return Response({"status": "posted", "message": "Content posted successfully."})
        else:
            return Response({"status": "error", "message": "Failed to post to LinkedIn."}, status=500)

class LinkedInTokenExchangeView(APIView):
    def post(self, request):
        """
        Exchanges auth code for access token.
        """
        auth_code = request.data.get("auth_code")
        if not auth_code:
            return Response({"error": "Auth code required."}, status=400)

        # Exchange auth code with LinkedIn (placeholder logic)
        # Replace with your real token exchange implementation
        token_response = {
            "access_token": f"fake_access_token_for_{auth_code}",
            "expires_in": 3600
        }

        return Response({"access_token": token_response["access_token"]})

def evaluate_response(user_prompt, response, extracted_data):
    eval_prompt = f"""Rate this AI response quality from 0.0 to 1.0:

User Query: {user_prompt}
AI Response: {response}
Data Available: {extracted_data[:1000]}...

Rate accuracy and relevance. Respond only with JSON:
{{"accuracy": 0.0-1.0, "relevance": 0.0-1.0, "overall": 0.0-1.0, "needs_retry": true/false}}"""

    try:
        eval_response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=eval_prompt
        )
        json_match = re.search(r'\{.*\}', eval_response.text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except:
        pass

    low_quality_signs = ["don't have enough", "cannot answer", "insufficient", "not enough details"]
    has_low_quality = any(sign in response.lower() for sign in low_quality_signs)

    return {
        "accuracy": 0.3 if has_low_quality else 0.7,
        "relevance": 0.4 if has_low_quality else 0.7,
        "overall": 0.35 if has_low_quality else 0.7,
        "needs_retry": has_low_quality or len(response) < 100
    }

class LLMAskView(APIView):
    def post(self, request):
        user_prompt = request.data.get("prompt")
        extracted_data = request.data.get("data", "")

        if not user_prompt:
            return Response({"error": "Prompt required"}, status=status.HTTP_400_BAD_REQUEST)

        # First attempt
        prompt = f"""You are an intelligent web content analyzer. Analyze the data and answer the user query accurately.

Data: {extracted_data}
User Query: {user_prompt}

Provide a comprehensive response based strictly on the provided data. Use specific examples and details from the data."""

        response_obj = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        response_text = response_obj.text

        eval_result = evaluate_response(user_prompt, response_text, extracted_data)

        if eval_result.get("needs_retry"):
            retry_prompt = f"""Your previous response was low quality. Improve it using the provided data.

Previous Response: {response_text}

User Query: {user_prompt}
Data: {extracted_data}

Provide a better, more detailed response using specific information from the data."""

            retry_response_obj = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=retry_prompt
            )
            response_text = retry_response_obj.text

        return Response({"response": response_text})
