# urls.py

from django.urls import path
from .views import LinkedInAuthCheckView, LLMAskView, LinkedInPostView

urlpatterns = [
    path('api/linkedin/check-auth/', LinkedInAuthCheckView.as_view()),
    path('api/ask', LLMAskView.as_view(), name='llm-ask'),
    path('api/linkedin/post', LinkedInPostView.as_view(), "Post-API")
]
