"""
Management command para limpar vídeos corporativos expirados.

Uso:
    python manage.py cleanup_corp_videos
    python manage.py cleanup_corp_videos --force   (remove TODOS)

Pode ser configurado como cron job no Railway ou scheduler.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Remove vídeos corporativos gerados que ultrapassaram o TTL de cache'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Remove TODOS os vídeos corporativos, ignorando TTL',
        )

    def handle(self, *args, **options):
        from core.video_generator import limpar_videos_expirados, _get_output_dir
        import os

        if options['force']:
            output_dir = _get_output_dir()
            removed = 0
            for f in output_dir.glob('*.mp4'):
                try:
                    f.unlink()
                    removed += 1
                except Exception as e:
                    self.stderr.write(f'Erro ao remover {f.name}: {e}')
            self.stdout.write(self.style.SUCCESS(f'{removed} vídeo(s) removido(s) (force).'))
        else:
            removed = limpar_videos_expirados()
            self.stdout.write(self.style.SUCCESS(f'{removed} vídeo(s) expirado(s) removido(s).'))
