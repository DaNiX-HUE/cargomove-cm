from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0006_vehicle_current_lat_vehicle_current_lng_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='shipment',
            name='delivery_type',
            field=models.CharField(
                choices=[('ECONOMY', 'Economy'), ('EXPRESS', 'Express'), ('SCHEDULED', 'Scheduled')],
                default='ECONOMY',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='shipment',
            name='shared_load',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='shipment',
            name='loading_assistance',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='shipment',
            name='special_handling',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='shipment',
            name='estimated_price_xaf',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='transportoffer',
            name='status',
            field=models.CharField(
                choices=[
                    ('PENDING', 'Pending'),
                    ('ACCEPTED', 'Accepted'),
                    ('REJECTED', 'Rejected'),
                    ('EXPIRED', 'Expired'),
                ],
                default='PENDING',
                max_length=10,
            ),
        ),
    ]
