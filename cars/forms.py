from django import forms
from django.forms import inlineformset_factory
from .models import Car, CarImage, CarInquiry


class CarForm(forms.ModelForm):
    """
    Main form for creating/editing car listings
    Custom widgets for better UX
    """
    class Meta:
        model = Car
        fields = [
            'title', 'make', 'model', 'year', 'price', 'mileage',
            'transmission', 'fuel_type', 'condition', 'description',
            'category', 'section', 'featured', 'location', 'color'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
                'placeholder': 'e.g., 2020 Toyota Corolla LE'
            }),
            'make': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent'
            }),
            'model': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
                'placeholder': 'e.g., Corolla, Camry, Accord'
            }),
            'year': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
                'placeholder': '2020',
                'min': '1990',
                'max': '2026'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
                'placeholder': '5000000',
                'step': '10000'
            }),
            'mileage': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
                'placeholder': '45000 (km)'
            }),
            'transmission': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent'
            }),
            'fuel_type': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent'
            }),
            'condition': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
                'rows': '6',
                'placeholder': 'Provide detailed information about the car...'
            }),
            'category': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent'
            }),
            'section': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent'
            }),
            'location': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
                'placeholder': 'e.g., Lagos, Abuja, Port Harcourt'
            }),
            'color': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
                'placeholder': 'e.g., Silver, Black, White'
            }),
            'featured': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-cyan-600 bg-gray-100 border-gray-300 rounded focus:ring-cyan-500'
            }),
        }
        labels = {
            'title': 'Car Title',
            'make': 'Make/Brand',
            'model': 'Model',
            'year': 'Year',
            'price': 'Price (₦)',
            'mileage': 'Mileage (km) - Optional',
            'transmission': 'Transmission',
            'fuel_type': 'Fuel Type',
            'condition': 'Condition',
            'description': 'Description',
            'category': 'Category',
            'section': 'Display Section (Optional)',
            'featured': 'Also mark as featured',
            'location': 'Location',
            'color': 'Color',
        }
    
    def clean_price(self):
        """Validate price is positive"""
        price = self.cleaned_data.get('price')
        if price and price <= 0:
            raise forms.ValidationError('Price must be greater than zero.')
        return price
    
    def clean_year(self):
        """Validate year is reasonable"""
        from datetime import datetime
        year = self.cleaned_data.get('year')
        current_year = datetime.now().year
        if year and (year < 1990 or year > current_year + 1):
            raise forms.ValidationError(f'Year must be between 1990 and {current_year + 1}.')
        return year


class CarImageForm(forms.ModelForm):
    """
    Form for individual car images
    """
    class Meta:
        model = CarImage
        fields = ['image', 'alt_text', 'is_primary']
        widgets = {
            'image': forms.FileInput(attrs={
                'class': 'block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 focus:outline-none',
                'accept': 'image/*'
            }),
            'alt_text': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
                'placeholder': 'Image description (optional)'
            }),
            'is_primary': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-cyan-600 bg-gray-100 border-gray-300 rounded focus:ring-cyan-500'
            }),
        }


# Formset for multiple image uploads
CarImageFormSet = inlineformset_factory(
    Car,
    CarImage,
    form=CarImageForm,
    extra=5,  # Allow up to 5 images initially
    max_num=10,  # Maximum 10 images per car
    can_delete=True,
    validate_max=True
)


class CarInquiryForm(forms.ModelForm):
    """
    Form for users to inquire about a car
    """
    class Meta:
        model = CarInquiry
        fields = ['name', 'email', 'phone', 'message']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
                'placeholder': 'Your Full Name',
                'required': True
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
                'placeholder': 'your.email@example.com',
                'required': True
            }),
            'phone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
                'placeholder': '+234 XXX XXX XXXX',
                'required': True
            }),
            'message': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
                'rows': '5',
                'placeholder': 'I am interested in this car. Please contact me with more details...',
                'required': True
            }),
        }
    
    def clean_phone(self):
        """Basic phone validation"""
        phone = self.cleaned_data.get('phone')
        # Remove spaces and hyphens
        phone = phone.replace(' ', '').replace('-', '')
        if not phone.isdigit() and not phone.startswith('+'):
            raise forms.ValidationError('Please enter a valid phone number.')
        return phone


class CarSearchForm(forms.Form):
    """
    Quick search form for homepage
    """
    search = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-6 py-4 text-lg border-2 border-gray-300 rounded-l-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
            'placeholder': 'Search by make, model, or keyword...'
        })
    )
    condition = forms.ChoiceField(
        choices=[('', 'All Conditions')] + list(Car._meta.get_field('condition').choices),
        required=False,
        widget=forms.Select(attrs={
            'class': 'px-4 py-4 border-2 border-l-0 border-gray-300 focus:ring-2 focus:ring-cyan-500 focus:border-transparent'
        })
    )
    max_price = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'px-4 py-4 border-2 border-l-0 border-gray-300 focus:ring-2 focus:ring-cyan-500 focus:border-transparent',
            'placeholder': 'Max Price'
        })
    )