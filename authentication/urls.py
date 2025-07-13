from django.urls import path
from .views import (
    LinkedInAuthCheckView,
    LinkedInGetTokenView,
    LinkedInPostView,
    LLMAskView,
    show_token
)

urlpatterns = [
    path('api/linkedin/check-auth/', LinkedInAuthCheckView.as_view()),
    path('api/linkedin/get-token/', LinkedInGetTokenView.as_view()),
    path('api/linkedin/post/', LinkedInPostView.as_view()),
    path('api/ask', LLMAskView.as_view(), name='llm-ask'),
    path('linkedin/token-page/', show_token, name='linkedin-token-page'),
]
