# urls.py

from django.urls import path
from .views import LinkedInAuthCheckView, LLMAskView

urlpatterns = [
    path('api/linkedin/check-auth/', LinkedInAuthCheckView.as_view()),
    path('api/ask', LLMAskView.as_view(), name='llm-ask'),
]
