from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ContactMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Nom complet')),
                ('email', models.EmailField(max_length=254, verbose_name='Email')),
                ('subject', models.CharField(choices=[('question', 'Question générale'), ('technical', 'Problème technique'), ('partnership', 'Partenariat'), ('other', 'Autre')], max_length=20, verbose_name='Sujet')),
                ('message', models.TextField(verbose_name='Message')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Date de création')),
                ('is_read', models.BooleanField(default=False, verbose_name='Lu')),
            ],
            options={
                'verbose_name': 'Message de contact',
                'verbose_name_plural': 'Messages de contact',
                'ordering': ['-created_at'],
            },
        ),
    ]