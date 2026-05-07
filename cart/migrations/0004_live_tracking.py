from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cart', '0003_equipmentmovement'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='live_tracking_expires',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='reservation',
            name='live_tracking_token',
            field=models.UUIDField(blank=True, db_index=True, null=True),
        ),
        migrations.CreateModel(
            name='LiveLocationPing',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('latitude', models.DecimalField(decimal_places=6, max_digits=9)),
                ('longitude', models.DecimalField(decimal_places=6, max_digits=9)),
                ('accuracy_m', models.FloatField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                (
                    'reservation',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='live_pings',
                        to='cart.reservation',
                    ),
                ),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='livelocationping',
            index=models.Index(fields=['reservation', 'created_at'], name='cart_liveping_res_created_idx'),
        ),
    ]
