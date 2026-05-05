from django.core.management.base import BaseCommand

from ai_recommendations.services.embedding_service import (
    cosine_similarity_score,
    generate_embedding,
)


class Command(BaseCommand):
    help = "Test AI recommendations by comparing one agent profile with multiple offers."

    def handle(self, *args, **options):
        agent_text = """
        Agent Profile:
        I am a mobile application developer specialized in React Native and Flutter.
        I build Android and iOS applications with modern UI/UX design.
        I have experience with REST APIs, Firebase, authentication, and clean mobile interfaces.
        I prefer mobile app projects, frontend development, and UI integration.
        Location: Tunis.
        Skills: React Native, Flutter, Dart, JavaScript, UI Design, Mobile Development, Firebase.
        """

        offers = [
            {
                "title": "Logo design for brand",
                "description": """
                 We are looking for a graphic designer to create a logo,
                 brand colors, typography, and social media templates
                 for a fashion clothing brand.
                 """,
                "expected": "NOT RELATED",
            },
            {
                "title": "Build a mobile app for restaurant booking",
                "description": """
                We need a developer to create an Android and iOS mobile application
                for restaurant reservations. The app should include authentication,
                booking management, modern UI screens, and API integration.
                """,
                "expected": "RELATED",
            },
            {
                "title": "React Native developer for delivery app",
                "description": """
                Looking for a React Native developer to build a delivery mobile app.
                The project includes user login, order tracking, maps integration,
                push notifications, and clean UI implementation.
                """,
                "expected": "RELATED",
            },
            {
                "title": "Flutter UI redesign for service marketplace",
                "description": """
                We already have a Flutter application and need someone to improve
                the UI, fix responsive layouts, connect screens to APIs,
                and polish the mobile user experience.
                """,
                "expected": "RELATED",
            },
            {
                "title": "Django backend API for admin dashboard",
                "description": """
                We need a backend developer to build REST APIs using Django REST Framework.
                The work includes database models, serializers, authentication,
                admin permissions, and PostgreSQL optimization.
                """,
                "expected": "NOT RELATED",
            },

            {
                "title": "Data analysis with Excel and Power BI",
                "description": """
                Need a data analyst to clean Excel files, create Power BI dashboards,
                analyze sales data, and prepare monthly business reports.
                """,
                "expected": "NOT RELATED",
            },
            {
                "title": "WordPress website for real estate agency",
                "description": """
                Looking for someone to create a WordPress website with property listings,
                contact forms, SEO setup, and basic website customization.
                """,
                "expected": "PARTIALLY RELATED",
            },
        ]

        self.stdout.write(self.style.SUCCESS("\nAI Recommendation Test Started"))
        self.stdout.write("=" * 80)
        self.stdout.write("AGENT DESCRIPTION:")
        self.stdout.write(agent_text.strip())
        self.stdout.write("=" * 80)

        agent_embedding = generate_embedding(agent_text)

        results = []

        for offer in offers:
            offer_text = f"""
            Offer Title: {offer["title"]}
            Offer Description: {offer["description"]}
            """

            offer_embedding = generate_embedding(offer_text)
            similarity = cosine_similarity_score(agent_embedding, offer_embedding)
            percentage = round(similarity * 100, 2)

            if percentage >= 65:
                match_level = "Strong match"
            elif percentage >= 50:
                match_level = "Medium match"
            elif percentage >= 35:
                match_level = "Weak match"
            else:
                match_level = "Not recommended"

            results.append(
                {
                    "title": offer["title"],
                    "description": offer["description"].strip(),
                    "expected": offer["expected"],
                    "percentage": percentage,
                    "match_level": match_level,
                }
            )

        results.sort(key=lambda item: item["percentage"], reverse=True)

        self.stdout.write("\nOFFER RECOMMENDATION RESULTS:")
        self.stdout.write("=" * 80)

        for index, result in enumerate(results, start=1):
            self.stdout.write(f"\n{index}. {result['title']}")
            self.stdout.write(f"Expected relation: {result['expected']}")
            self.stdout.write(f"AI similarity: {result['percentage']}%")
            self.stdout.write(f"Match level: {result['match_level']}")
            self.stdout.write("Description:")
            self.stdout.write(result["description"])
            self.stdout.write("-" * 80)

        self.stdout.write(self.style.SUCCESS("\nAI recommendation test completed."))