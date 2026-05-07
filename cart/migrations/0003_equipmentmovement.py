from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('equipment', '0001_initial'),
        ('cart', '0002_reservation_declared_location'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='EquipmentMovement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('movement_type', models.CharField(choices=[('declared', 'Déclaration initiale'), ('updated', 'Mise à jour emplacement'), ('admin_adjustment', 'Ajustement administrateur')], default='updated', max_length=30)),
                ('old_latitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('old_longitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('old_location_name', models.CharField(blank=True, max_length=255)),
                ('new_latitude', models.DecimalField(decimal_places=6, max_digits=9)),
                ('new_longitude', models.DecimalField(decimal_places=6, max_digits=9)),
                ('new_location_name', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('equipment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='movements', to='equipment.equipment')),
                ('reservation', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='movements', to='cart.reservation')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='equipment_movements', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
