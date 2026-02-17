from django.core.management.base import BaseCommand
from django.conf import settings
import os
from core.models import Video, Cliente, AppVersion


class Command(BaseCommand):
    help = 'Remove registros de arquivos que não existem no sistema de arquivos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostra o que seria removido sem executar',
        )
        parser.add_argument(
            '--model',
            choices=['video', 'cliente', 'appversion', 'all'],
            default='all',
            help='Modelo para verificar (padrão: all)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        model_choice = options['model']

        self.stdout.write('Verificando arquivos órfãos...')

        if model_choice in ['video', 'all']:
            self.check_videos(dry_run)
        if model_choice in ['cliente', 'all']:
            self.check_clientes(dry_run)
        if model_choice in ['appversion', 'all']:
            self.check_app_versions(dry_run)

        if dry_run:
            self.stdout.write(self.style.WARNING('Modo dry-run: nenhum registro foi removido'))
        else:
            self.stdout.write(self.style.SUCCESS('Limpeza concluída'))

    def check_videos(self, dry_run):
        videos = Video.objects.all()
        orphaned = []

        for video in videos:
            try:
                if video.arquivo and not os.path.exists(video.arquivo.path):
                    orphaned.append(video)
            except (ValueError, OSError, AttributeError) as e:
                # Arquivo com path inválido ou erro ao acessar
                self.stdout.write(self.style.WARNING(f'Erro ao verificar vídeo {video.id}: {str(e)}'))
                orphaned.append(video)

        if orphaned:
            self.stdout.write(self.style.WARNING(f'Encontrados {len(orphaned)} vídeos com arquivos inexistentes:'))
            for video in orphaned:
                arquivo_path = 'N/A'
                try:
                    if video.arquivo:
                        arquivo_path = video.arquivo.path
                except:
                    arquivo_path = 'Caminho inválido'
                self.stdout.write(f'  - {video} (ID: {video.id}) - {arquivo_path}')
                if not dry_run:
                    video.delete()
                    self.stdout.write(self.style.SUCCESS(f'    Removido'))
        else:
            self.stdout.write(self.style.SUCCESS('Nenhum vídeo órfão encontrado'))

    def check_clientes(self, dry_run):
        clientes = Cliente.objects.exclude(contrato__isnull=True)
        orphaned = []

        for cliente in clientes:
            if cliente.contrato and not os.path.exists(cliente.contrato.path):
                orphaned.append(cliente)

        if orphaned:
            self.stdout.write(f'Encontrados {len(orphaned)} clientes com contratos inexistentes:')
            for cliente in orphaned:
                self.stdout.write(f'  - {cliente} (ID: {cliente.id}) - {cliente.contrato.path}')
                if not dry_run:
                    cliente.contrato = None
                    cliente.save()
                    self.stdout.write(f'    Contrato removido')
        else:
            self.stdout.write('Nenhum contrato órfão encontrado')

    def check_app_versions(self, dry_run):
        app_versions = AppVersion.objects.all()
        orphaned = []

        for app_version in app_versions:
            if app_version.arquivo_apk and not os.path.exists(app_version.arquivo_apk.path):
                orphaned.append(app_version)

        if orphaned:
            self.stdout.write(f'Encontrados {len(orphaned)} app versions com arquivos inexistentes:')
            for app_version in orphaned:
                self.stdout.write(f'  - {app_version} (ID: {app_version.id}) - {app_version.arquivo_apk.path}')
                if not dry_run:
                    app_version.delete()
                    self.stdout.write(f'    Removido')
        else:
            self.stdout.write('Nenhuma app version órfã encontrada')