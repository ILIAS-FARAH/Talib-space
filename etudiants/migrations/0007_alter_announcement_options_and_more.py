# Generated by Django 5.2.2 on 2025-06-27 12:41

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('etudiants', '0006_quizattempt_delete_favorite'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='announcement',
            options={'ordering': ['-created_at'], 'verbose_name': 'Announcement', 'verbose_name_plural': 'Announcements'},
        ),
        migrations.AlterModelOptions(
            name='announcementimage',
            options={'ordering': ['order', 'created_at'], 'verbose_name': 'Announcement Image', 'verbose_name_plural': 'Announcement Images'},
        ),
        migrations.AlterModelOptions(
            name='quizattempt',
            options={'ordering': ['-created_at'], 'verbose_name': 'Quiz Attempt', 'verbose_name_plural': 'Quiz Attempts'},
        ),
        migrations.RemoveField(
            model_name='announcement',
            name='image',
        ),
        migrations.AddField(
            model_name='announcement',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='announcementimage',
            name='caption',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='announcementimage',
            name='order',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='quizattempt',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='announcement',
            name='amenities',
            field=models.CharField(blank=True, help_text='Comma-separated list of amenities', max_length=255),
        ),
        migrations.AlterField(
            model_name='announcement',
            name='room_type',
            field=models.CharField(choices=[('single_room', 'Single Room'), ('shared_room', 'Shared Room'), ('apartment', 'Entire Apartment')], default='shared_room', max_length=20),
        ),
        migrations.AlterField(
            model_name='quizattempt',
            name='announcement',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='quiz_attempts', to='etudiants.announcement'),
        ),
        migrations.AlterField(
            model_name='quizattempt',
            name='answers',
            field=models.JSONField(help_text="Stores the user's quiz answers and metadata"),
        ),
        migrations.AlterField(
            model_name='quizattempt',
            name='score',
            field=models.IntegerField(blank=True, help_text='Compatibility score (0-100)', null=True),
        ),
        migrations.AlterField(
            model_name='quizattempt',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='quiz_attempts', to=settings.AUTH_USER_MODEL),
        ),
    ]
