import logging
import os

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'MediaExpand Core'

    def ready(self):
        """
        Inicia o APScheduler que roda check_offline_devices() periodicamente.

        Guardas:
        - Só inicia no processo principal (não no reloader filho, não em manage.py commands).
        - Evita dupla inicialização com uma flag de módulo.
        """
        # Não rodar em management commands (migrate, collectstatic, etc.)
        import sys
        if len(sys.argv) > 1 and sys.argv[1] in (
            'migrate', 'makemigrations', 'collectstatic', 'createcachetable',
            'shell', 'dbshell', 'test', 'check',
            'create_owner', 'check_devices_offline',
            'cleanup_orphaned_files', 'cleanup_corp_videos',
        ):
            return

        # Evitar duplo start quando Django usa o autoreloader (RUN_MAIN é definido pelo reloader)
        if os.environ.get('RUN_MAIN') == 'true':
            return

        self._start_scheduler()

    @staticmethod
    def _start_scheduler():
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.interval import IntervalTrigger
            from django.conf import settings

            interval = getattr(settings, 'DEVICE_CHECK_INTERVAL_SECONDS', 60)

            scheduler = BackgroundScheduler(timezone='America/Sao_Paulo')
            scheduler.add_job(
                _run_check_offline,
                trigger=IntervalTrigger(seconds=interval),
                id='check_offline_devices',
                replace_existing=True,
                misfire_grace_time=30,
            )
            scheduler.start()
            logger.info("alerts: scheduler iniciado — verificação a cada %ds.", interval)
        except ImportError:
            logger.warning("alerts: APScheduler não instalado, scheduler desativado.")
        except Exception as exc:
            logger.error("alerts: falha ao iniciar scheduler: %s", exc)


def _run_check_offline():
    """Wrapper seguro chamado pelo scheduler."""
    try:
        from core.alerts import check_offline_devices
        check_offline_devices()
    except Exception as exc:
        logger.error("alerts: erro no job check_offline_devices: %s", exc)
