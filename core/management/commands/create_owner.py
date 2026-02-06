from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Cria o usuário OWNER inicial do sistema'

    def handle(self, *args, **kwargs):
        if User.objects.filter(role='OWNER').exists():
            self.stdout.write(self.style.WARNING('Já existe um usuário OWNER no sistema.'))
            return

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
