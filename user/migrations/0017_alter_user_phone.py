# Generated by Django 4.2.7 on 2024-03-12 15:17

from django.db import migrations, models
import user.models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0016_alter_user_phone'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='phone',
            field=models.CharField(max_length=14, null=True, validators=[user.models.phone_validator]),
        ),
    ]
