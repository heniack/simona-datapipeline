from django.core.management.base import BaseCommand
from core.models import GoogleDriveToken


class Command(BaseCommand):
    help = 'Elimina los tokens de Google Drive para forzar re-autenticación'

    def add_arguments(self, parser):
        parser.add_argument('--user', type=str, help='Username del usuario (opcional, si no se pone elimina todos)')

    def handle(self, *args, **options):
        username = options.get('user')
        
        if username:
            tokens = GoogleDriveToken.objects.filter(user__username=username)
            if not tokens.exists():
                self.stdout.write(self.style.WARNING(f'No se encontró token para el usuario: {username}'))
                return
        else:
            tokens = GoogleDriveToken.objects.all()
        
        count = tokens.count()
        tokens.delete()
        
        self.stdout.write(self.style.SUCCESS(f'\n✓ Eliminados {count} token(s) de Google Drive\n'))
        self.stdout.write(self.style.WARNING('👉 Ahora iniciá el servidor y andá a la lista de conectores'))
        self.stdout.write(self.style.WARNING('   Vas a ver un mensaje para autenticarte con Google'))
        self.stdout.write(self.style.WARNING('   Esto te dará un token CON refresh_token para auto-renovación\n'))
