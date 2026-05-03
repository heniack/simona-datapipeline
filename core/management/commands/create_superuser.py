from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import UserProfile


class Command(BaseCommand):
    help = 'Crea el superuser si no existe'

    def handle(self, *args, **options):
        username = 'administrator'
        if not User.objects.filter(username=username).exists():
            user = User.objects.create_superuser(username=username, email='', password='12345678')
            UserProfile.objects.get_or_create(user=user, defaults={'role': 'admin'})
            self.stdout.write(self.style.SUCCESS(f'Superuser "{username}" creado'))
        else:
            user = User.objects.get(username=username)
            # Forzar la contraseña por si no se guardó bien
            user.set_password('12345678')
            user.save()
            UserProfile.objects.get_or_create(user=user, defaults={'role': 'admin'})
            self.stdout.write(self.style.WARNING(f'Superuser "{username}" ya existe, contraseña reseteada'))
