from django import forms
from django.core.exceptions import ValidationError
from .models import Announcement, AnnouncementImage
import os

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

    def __init__(self, attrs=None):
        default_attrs = {'multiple': True}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = []
            for file in data:
                if file:
                    result.append(single_file_clean(file, initial))
            return result
        return [single_file_clean(data, initial)] if data else []

class AnnouncementForm(forms.ModelForm):
    amenities = forms.MultipleChoiceField(
        choices=Announcement.AMENITIES_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    
    images = MultipleFileField(
        required=False,
        label='Upload Images',
        help_text='Upload multiple images (max 10). First image will be the main photo.',
    )

    class Meta:
        model = Announcement
        fields = ['title', 'description', 'city', 'price', 'room_type', 'gender_preference', 'amenities']
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Describe your accommodation...'
            }),
            'title': forms.TextInput(attrs={
                'placeholder': 'e.g., Cozy Room Near University'
            }),
            'city': forms.TextInput(attrs={
                'placeholder': 'e.g., Fes, Rabat, Casablanca'
            }),
            'price': forms.NumberInput(attrs={
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        if self.instance and self.instance.amenities:
            self.fields['amenities'].initial = self.instance.get_amenities_list()

    def clean_images(self):
        images = self.cleaned_data.get('images', [])
        
        if len(images) > 10:
            raise ValidationError('Maximum 10 images allowed.')
        
        for image in images:
            if image.size > 10 * 1024 * 1024:
                raise ValidationError(f'{image.name} is too large (max 10MB).')
            
            ext = os.path.splitext(image.name)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                raise ValidationError(f'{image.name} has invalid format.')
        
        return images

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if self.request:
            instance.user = self.request.user
            
        instance.amenities = ','.join(self.cleaned_data.get('amenities', []))
        
        if commit:
            instance.save()
            
            images = self.cleaned_data.get('images', [])
            if images:
                # Delete existing images if updating
                if self.instance.pk:
                    instance.images.all().delete()
                
                # Create new images
                for i, image in enumerate(images):
                    AnnouncementImage.objects.create(
                        announcement=instance,
                        image=image,
                        order=i
                    )
            
            self.save_m2m()
        
        return instance

class AnnouncementUpdateForm(AnnouncementForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['images'].required = False
        self.fields['images'].help_text = 'Upload new images to replace existing ones.'

    def save(self, commit=True):
        instance = super(forms.ModelForm, self).save(commit=False)
        instance.amenities = ','.join(self.cleaned_data.get('amenities', []))
        
        if commit:
            instance.save()
            
            new_images = self.cleaned_data.get('images', [])
            if new_images:
                # Delete existing images
                instance.images.all().delete()
                
                # Create new images
                for i, image in enumerate(new_images):
                    AnnouncementImage.objects.create(
                        announcement=instance,
                        image=image,
                        order=i
                    )
            
            self.save_m2m()
        
        return instance