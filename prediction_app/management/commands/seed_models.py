from django.core.management.base import BaseCommand
from prediction_app.models import DiseaseModel


class Command(BaseCommand):
    help = 'Seed disease model records in the database'

    def handle(self, *args, **kwargs):
        diseases = [
            ('diabetes', 0.85),
            ('heart', 0.87),
            ('kidney', 0.83),
            ('parkinson', 0.89),
            ('breast_cancer', 0.92),
            ('liver', 0.81),
        ]

        for name, accuracy in diseases:
            obj, created = DiseaseModel.objects.update_or_create(
                name=name,
                defaults={
                    'accuracy': accuracy,
                    'is_active': True,
                    'model_file': f'ml_models/{name}_model.pkl',
                    'scaler_file': f'ml_models/scalers/{name}_scaler.pkl',
                }
            )
            status = 'Created' if created else 'Updated'
            self.stdout.write(f'{status}: {name}')

        self.stdout.write(self.style.SUCCESS('Disease models seeded successfully.'))
