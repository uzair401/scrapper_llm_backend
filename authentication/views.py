from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from allauth.socialaccount.models import SocialAccount, SocialToken
from django.conf import settings
import os
import re
import json
from dotenv import load_dotenv
from google import genai
from allauth.account.signals import user_logged_in
from django.dispatch import receiver

load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

@receiver(user_logged_in)
def generate_auth_token_on_login(request, user, **kwargs):
    token, created = Token.objects.get_or_create(user=user)
    print(f"Token generated for user {user.username}: {token.key}")

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

@method_decorator(csrf_exempt, name='dispatch')
class LinkedInAuthCheckView(APIView):
    def get(self, request):
        user = request.user
        if not user.is_authenticated:
            login_url = f"{settings.SITE_URL}/accounts/linkedin_oauth2/login/"
            return Response({"status": "login_required", "login_url": login_url}, status=401)

        account = SocialAccount.objects.filter(user=user, provider='linkedin_oauth2').first()
        if not account:
            login_url = f"{settings.SITE_URL}/accounts/linkedin_oauth2/login/"
            return Response({"status": "login_required", "login_url": login_url}, status=401)

        token_obj = SocialToken.objects.filter(account=account).first()
        if not token_obj:
            login_url = f"{settings.SITE_URL}/accounts/linkedin_oauth2/login/"
            return Response({"status": "login_required", "login_url": login_url}, status=401)

        return Response({"access_token": token_obj.token})

@method_decorator(csrf_exempt, name='dispatch')
class LinkedInGetTokenView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        account = SocialAccount.objects.filter(user=user, provider='linkedin_oauth2').first()
        if not account:
            return Response({"error": "LinkedIn account not connected."}, status=400)

        token_obj = SocialToken.objects.filter(account=account).first()
        if not token_obj:
            return Response({"error": "Token not found."}, status=400)

        return Response({"access_token": token_obj.token})

@method_decorator(csrf_exempt, name='dispatch')
class LinkedInPostView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        content = request.data.get("content")
        user = request.user

        if not content:
            return Response({"error": "Content is required."}, status=400)

        account = SocialAccount.objects.filter(user=user, provider='linkedin_oauth2').first()
        if not account:
            login_url = f"{settings.SITE_URL}/accounts/linkedin_oauth2/login/"
            return Response({"status": "login_required", "login_url": login_url}, status=401)

        token_obj = SocialToken.objects.filter(account=account).first()
        linkedin_token = token_obj.token if token_obj else None

        if not linkedin_token:
            login_url = f"{settings.SITE_URL}/accounts/linkedin_oauth2/login/"
            return Response({"status": "login_required", "login_url": login_url}, status=401)

        print(f"Posting to LinkedIn with token: {linkedin_token} and content: {content}")
        return Response({"status": "posted", "message": "Content posted successfully."})

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
