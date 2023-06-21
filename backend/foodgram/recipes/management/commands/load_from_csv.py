from csv import DictReader

from django.core.management import BaseCommand
from recipes.models import Ingredient


class LoadCsvCommand(BaseCommand):
    """Загружает из csv-файла в БД из папки data/."""

    def handle(self, *args, **options):
        for row in DictReader(open('data/ingredients.csv',
                                   encoding="utf8")):
            ingredient = Ingredient(
                name=row['name'],
                measurement_unit=row['measurement_unit']
            )
            ingredient.save()
