from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Verifica dispositivos offline e envia alertas por e-mail (Brevo SMTP).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Lista dispositivos offline sem enviar e-mail.',
        )

    def handle(self, *args, **options):
        from django.conf import settings
        from django.utils import timezone
        from core.models import DispositivoTV
        from core.alerts import check_offline_devices

        threshold = getattr(settings, 'DEVICE_OFFLINE_THRESHOLD_MINUTES', 10)
        cutoff = timezone.now() - timezone.timedelta(minutes=threshold)

        if options['dry_run']:
            offline = DispositivoTV.objects.filter(
                ativo=True,
                ultima_sincronizacao__isnull=False,
                ultima_sincronizacao__lt=cutoff,
            ).select_related('municipio')

            self.stdout.write(self.style.WARNING(
                f'[dry-run] Threshold: {threshold} min | Corte: {cutoff:%d/%m/%Y %H:%M:%S}'
            ))
            if not offline.exists():
                self.stdout.write(self.style.SUCCESS('Nenhum dispositivo offline.'))
                return

            for d in offline:
                alerta = '📤 alerta já enviado' if d.alerta_desconexao_enviado else '🔴 alerta PENDENTE'
                ultima = timezone.localtime(d.ultima_sincronizacao).strftime('%d/%m %H:%M:%S')
                self.stdout.write(f'  {d.nome} ({d.municipio}) | último: {ultima} | {alerta}')
            return

        self.stdout.write('Verificando dispositivos offline...')
        alerted = check_offline_devices()
        if alerted:
            self.stdout.write(self.style.WARNING(f'{alerted} alerta(s) enviado(s).'))
        else:
            self.stdout.write(self.style.SUCCESS('Nenhum novo dispositivo offline.'))
