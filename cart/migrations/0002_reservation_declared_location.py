from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cart', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='declared_latitude',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AddField(
            model_name='reservation',
            name='declared_location_name',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='reservation',
            name='declared_longitude',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AddField(
            model_name='reservation',
            name='location_declared_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
