from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='due_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
