import django_filters
from django import forms
from django.db.models import Q
from .models import Car, SECTION_CHOICES

class CarFilter(django_filters.FilterSet):
    """
    Comprehensive filter for car listings with special handling for 100M+ prices and 100k+ mileage
    """
   
    # Make filter: Dynamic choices from existing distinct makes in DB
    make = django_filters.ChoiceFilter(
        empty_label="All Makes",
        widget=forms.Select
    )
   
    # Model search (contains)
    model = django_filters.CharFilter(
        lookup_expr='icontains',
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal focus:border-transparent',
            'placeholder': 'e.g., Corolla, Camry'
        })
    )
   
    # Price range filters with special handling for 100M+
    min_price = django_filters.NumberFilter(
        method='filter_min_price',
        label='Min Price (₦)',
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal focus:border-transparent',
            'step': '100000'
        })
    )
   
    max_price = django_filters.NumberFilter(
        method='filter_max_price',
        label='Max Price (₦)',
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal focus:border-transparent',
            'step': '100000'
        })
    )
   
    # Mileage range filters with special handling for 100k+
    min_mileage = django_filters.NumberFilter(
        method='filter_min_mileage',
        label='Min Mileage (km)',
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal focus:border-transparent',
            'step': '1000'
        })
    )
   
    max_mileage = django_filters.NumberFilter(
        method='filter_max_mileage',
        label='Max Mileage (km)',
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal focus:border-transparent',
            'step': '1000'
        })
    )
   
    # Year range
    min_year = django_filters.NumberFilter(
        field_name='year',
        lookup_expr='gte',
        label='Min Year',
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal focus:border-transparent',
            'min': '1990',
            'max': '2024'
        })
    )
   
    max_year = django_filters.NumberFilter(
        field_name='year',
        lookup_expr='lte',
        label='Max Year',
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal focus:border-transparent',
            'min': '1990',
            'max': '2024'
        })
    )
   
    # Transmission filter
    transmission = django_filters.ChoiceFilter(
        choices=Car._meta.get_field('transmission').choices,
        empty_label="All Transmissions",
        widget=forms.Select
    )
   
    # Fuel type filter
    fuel_type = django_filters.ChoiceFilter(
        choices=Car._meta.get_field('fuel_type').choices,
        empty_label="All Fuel Types",
        widget=forms.Select
    )
   
    # Condition filter
    condition = django_filters.ChoiceFilter(
        choices=Car._meta.get_field('condition').choices,
        empty_label="All Conditions",
        widget=forms.Select
    )
   
    # Section filter
    section = django_filters.ChoiceFilter(
        choices=SECTION_CHOICES,
        empty_label="All Sections",
        widget=forms.Select
    )
   
    # Location filter
    location = django_filters.CharFilter(
        lookup_expr='icontains',
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal focus:border-transparent',
            'placeholder': 'e.g., Lagos, Abuja'
        })
    )
   
    # Featured cars
    featured = django_filters.BooleanFilter(
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-teal bg-gray-100 border-gray-300 rounded focus:ring-teal'
        })
    )
   
    # Ordering
    ordering = django_filters.OrderingFilter(
        fields=(
            ('created_at', 'created_at'),
            ('price', 'price'),
            ('year', 'year'),
            ('mileage', 'mileage'),
            ('views', 'views'),
        ),
        field_labels={
            'created_at': 'Date Added',
            'price': 'Price',
            'year': 'Year',
            'mileage': 'Mileage',
            'views': 'Popularity',
        },
        widget=forms.Select,
        label='Sort By'
    )
   
    class Meta:
        model = Car
        fields = []
   
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Dynamically populate make choices from distinct values in DB
        makes = Car.objects.values_list('make', flat=True).distinct().order_by('make')
        self.filters['make'].extra['choices'] = [(make, make) for make in makes if make]
        
        # Apply attrs here for all Select widgets
        attrs = {
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal focus:border-transparent'
        }
        for field_name in ['make', 'transmission', 'fuel_type', 'condition', 'section', 'ordering']:
            if field_name in self.form.fields:
                self.form.fields[field_name].widget.attrs.update(attrs)
   
    def filter_min_price(self, queryset, name, value):
        """Custom filter for min price"""
        if value:
            return queryset.filter(price__gte=value)
        return queryset
    
    def filter_max_price(self, queryset, name, value):
        """Custom filter for max price - empty means 100M+"""
        if value:
            return queryset.filter(price__lte=value)
        return queryset
    
    def filter_min_mileage(self, queryset, name, value):
        """Custom filter for min mileage"""
        if value:
            return queryset.filter(mileage__gte=value)
        return queryset
    
    def filter_max_mileage(self, queryset, name, value):
        """Custom filter for max mileage - empty means 100k+"""
        if value:
            return queryset.filter(mileage__lte=value)
        return queryset
    
    @property
    def qs(self):
        """
        Override to add default ordering and handle unlimited filtering for price and mileage
        """
        queryset = super().qs
        
        # Handle price filtering with 100M+ logic
        min_price = self.data.get('min_price')
        max_price = self.data.get('max_price')
        
        # If min_price is set but max_price is empty, it means 100M+
        if min_price and not max_price:
            queryset = queryset.filter(price__gte=min_price)
        # If both are set, filter normally
        elif min_price and max_price:
            queryset = queryset.filter(price__gte=min_price, price__lte=max_price)
        # If only max_price is set
        elif max_price and not min_price:
            queryset = queryset.filter(price__lte=max_price)
        
        # Handle mileage filtering with 100k+ logic
        min_mileage = self.data.get('min_mileage')
        max_mileage = self.data.get('max_mileage')
        
        # If min_mileage is set but max_mileage is empty, it means 100k+
        if min_mileage and not max_mileage:
            queryset = queryset.filter(mileage__gte=min_mileage)
        # If both are set, filter normally
        elif min_mileage and max_mileage:
            queryset = queryset.filter(mileage__gte=min_mileage, mileage__lte=max_mileage)
        # If only max_mileage is set
        elif max_mileage and not min_mileage:
            queryset = queryset.filter(mileage__lte=max_mileage)
        
        # Default to newest first if no ordering specified
        if not self.data.get('ordering'):
            return queryset.order_by('-created_at')
        
        return queryset