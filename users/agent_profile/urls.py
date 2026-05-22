from django.urls import path
from .views import AgentProfileView, AgentPublicProfileView

urlpatterns = [
    path("me/", AgentProfileView.as_view(), name="agent-profile"),
    path("<int:user_id>/", AgentPublicProfileView.as_view(), name="agent-public-profile"),
]