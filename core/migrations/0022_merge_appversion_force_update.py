from django.db import migrations


class Migration(migrations.Migration):
    """
    Migration de merge para resolver conflito entre:
      - 0012_appversion_force_update  (campo force_update em AppVersion)
      - 0021_video_orientacao         (cadeia principal do servidor)
    """

    dependencies = [
        ('core', '0012_appversion_force_update'),
        ('core', '0021_video_orientacao'),
    ]

    operations = [
    ]
