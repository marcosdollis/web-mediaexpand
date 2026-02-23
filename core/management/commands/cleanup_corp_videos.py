"""
Management command para limpar imagens corporativas expiradas.

Uso:
    python manage.py cleanup_corp_videos
    python manage.py cleanup_corp_videos --force   (remove TODAS)
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Remove imagens corporativas que ultrapassaram o TTL de cache'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Remove TODAS as imagens corporativas, ignorando TTL',
        )

    def handle(self, *args, **options):
        from core.image_generator import limpar_imagens_expiradas, _get_output_dir

        if options['force']:
            output_dir = _get_output_dir()
            removed = 0
            for f in output_dir.glob('*.png'):
                try:
                    f.unlink()
                    removed += 1
                except Exception as e:
                    self.stderr.write(f'Erro ao remover {f.name}: {e}')
            self.stdout.write(self.style.SUCCESS(f'{removed} imagem(ns) removida(s) (force).'))
        else:
            removed = limpar_imagens_expiradas()
            self.stdout.write(self.style.SUCCESS(f'{removed} imagem(ns) expirada(s) removida(s).'))
