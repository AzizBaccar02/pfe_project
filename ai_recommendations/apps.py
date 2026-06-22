#C:\Users\Lenovo\django_project\pfe_project2\pfe_project\ai_recommendations\apps.py

from django.apps import AppConfig


class AiRecommendationsConfig(AppConfig):
    name = 'ai_recommendations'

    def ready(self):
        import threading

        def warm_embedding_model():
            try:
                from ai_recommendations.services.embedding_service import (
                    get_embedding_model,
                )

                get_embedding_model()
            except Exception:
                pass

        threading.Thread(target=warm_embedding_model, daemon=True).start()
