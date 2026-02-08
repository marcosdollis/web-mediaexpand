from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os

User = get_user_model()


class Command(BaseCommand):
    help = 'Cria o usuário OWNER inicial do sistema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--noinput',
            action='store_true',
            help='Não solicita entrada do usuário (modo não-interativo)',
        )

    def handle(self, *args, **options):
        if User.objects.filter(role='OWNER').exists():
            self.stdout.write(self.style.WARNING('Já existe um usuário OWNER no sistema.'))
            return

        # Verificar se há variáveis de ambiente (deploy automático)
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
        
        if username and email and password:
            # Modo automático (deploy)
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=os.environ.get('DJANGO_SUPERUSER_FIRST_NAME', 'Admin'),
                last_name=os.environ.get('DJANGO_SUPERUSER_LAST_NAME', 'MediaExpand'),
                password=password,
                role='OWNER',
                is_staff=True,
                is_superuser=True
            )
            self.stdout.write(self.style.SUCCESS(f'✓ Usuário OWNER "{username}" criado automaticamente!'))
        elif options.get('noinput'):
            # Modo noinput mas sem variáveis - apenas avisar
            self.stdout.write(self.style.WARNING('Modo --noinput ativo, mas variáveis de ambiente não configuradas.'))
            self.stdout.write(self.style.WARNING('Configure DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL e DJANGO_SUPERUSER_PASSWORD.'))
            self.stdout.write(self.style.WARNING('Pulando criação do usuário OWNER.'))
        else:
            # Modo interativo (desenvolvimento local)
            self.stdout.write(self.style.SUCCESS('\n=== Criação do Usuário OWNER (Dono) ===\n'))
            
            username = input('Username: ')
            email = input('Email: ')
            first_name = input('Nome: ')
            last_name = input('Sobrenome: ')
            password = input('Senha: ')
            
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=password,
                role='OWNER',
                is_staff=True,
                is_superuser=True
            )
            
            self.stdout.write(self.style.SUCCESS(f'\n✓ Usuário OWNER "{username}" criado com sucesso!'))
            self.stdout.write(self.style.SUCCESS('Este usuário tem acesso total ao sistema.\n'))
