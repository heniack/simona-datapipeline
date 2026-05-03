from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Crea el superuser si no existe'

    def handle(self, *args, **options):
        username = 'administrator'
        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username=username, email='', password='12345678')
            self.stdout.write(self.style.SUCCESS(f'Superuser "{username}" creado'))
        else:
            self.stdout.write(self.style.WARNING(f'Superuser "{username}" ya existe'))
