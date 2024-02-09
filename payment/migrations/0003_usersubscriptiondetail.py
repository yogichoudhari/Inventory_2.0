# Generated by Django 4.2.7 on 2024-02-05 19:14

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('payment', '0002_alter_subscription_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserSubscriptionDetail',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subscription_id', models.CharField(max_length=30)),
                ('status', models.CharField(choices=[('A', 'Active'), ('E', 'Expired')], max_length=35)),
                ('end_on', models.DateField()),
                ('billing', models.CharField(max_length=20)),
                ('name', models.CharField(max_length=35)),
                ('paid', models.BooleanField(default=False)),
                ('coupon', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='payment.coupon')),
            ],
        ),
    ]