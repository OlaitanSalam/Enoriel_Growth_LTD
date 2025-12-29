from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.db.models import Prefetch, Q, F
from django.contrib import messages
from django.core.cache import cache
from django_filters.views import FilterView
from .models import Car, CarImage, Category, CarInquiry, CarBooking, BookingMessage, BookingActivity
from .forms import CarForm, CarImageFormSet, CarInquiryForm
from .filters import CarFilter
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods 
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.utils import timezone
from django.utils.dateparse import parse_datetime



RATE_LIMIT_DECORATOR = method_decorator(
    ratelimit(key='ip', rate='3/m', method='POST', block=True),
    name='post' # Apply the decorator specifically to the 'post' method
)



class HomeView(ListView):
    """..."""
    model = Car
    template_name = 'cars/home.html'
    context_object_name = 'cars'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        
        # OPTIMIZATION: Prefetch images to avoid N+1 queries
        def get_cars_with_images(queryset):
            """Helper to fetch cars with their first image"""
            cars = list(queryset.select_related('category'))
            car_ids = [car.id for car in cars]
            
            if car_ids:
                first_images = {}
                for img in CarImage.objects.filter(car_id__in=car_ids).order_by('car_id', 'order', '-is_primary'):
                    if img.car_id not in first_images:
                        first_images[img.car_id] = img
                
                for car in cars:
                    car.prefetched_image = first_images.get(car.id)
            
            return cars
        
        # Get different sections (limit to 6 for speed)
        sections_data = {
            'sweet_deals': get_cars_with_images(
                Car.objects.filter(section='sweet_deals')[:8]
            ),
            'foreign_used': get_cars_with_images(
                Car.objects.filter(Q(section='foreign_used') | Q(condition='foreign_used'))[:8]
            ),
            'local_used': get_cars_with_images(
                Car.objects.filter(Q(section='local_used') | Q(condition='local_used'))[:8]
            ),
            'new_cars': get_cars_with_images(
                Car.objects.filter(Q(section='new_cars') | Q(condition='new'))[:8]
            ),
            'latest_listings': get_cars_with_images(
                Car.objects.order_by('-created_at')[:6]
            ),
            'categories': list(Category.objects.all().order_by('name')),
        }
        
        categories = list(Category.objects.all().order_by('name'))
        
        # Get first category (default) - alphabetically first
        if categories:
            default_category = categories[0]
            # Get cars for first category (10 cars)
            category_cars = list(Car.objects.filter(
                category=default_category
            ).select_related('category')[:10])
        else:
            default_category = None
            category_cars = []
        
        sections_data['default_category'] = default_category
        sections_data['category_cars'] = category_cars
    
        
        
        context.update(sections_data)
        return context


@require_http_methods(["GET"])
def get_category_cars(request):
    """
    API endpoint to get cars for a specific category
    FIX: Get ALL cars (not limited to 10) for horizontal scroll carousel
    FIX: Use manual prefetch_image method instead of prefetch_related
    """
    category_id = request.GET.get('category_id')
    
    if not category_id:
        return JsonResponse({'error': 'Category ID required'}, status=400)
    
    try:
        category = Category.objects.get(id=category_id)
        
        # FIX: Get ALL cars from category (no limit) for 10-per-row carousel
        cars = list(Car.objects.filter(
            category=category
        ).select_related('category'))
        
        # FIX: Manually fetch first image for each car (same as HomeView)
        if cars:
            car_ids = [car.id for car in cars]
            first_images = {}
            for img in CarImage.objects.filter(car_id__in=car_ids).order_by('car_id', 'order', '-is_primary'):
                if img.car_id not in first_images:
                    first_images[img.car_id] = img
            
            for car in cars:
                car.prefetched_image = first_images.get(car.id)
        
        # Format response
        cars_data = []
        for car in cars:
            # FIX: Use prefetched_image (manual fetch) instead of prefetch_related
            image_url = car.prefetched_image.image.url if car.prefetched_image else '/static/images/placeholder.png'
            
            cars_data.append({
                'id': car.id,
                'title': car.title,
                'slug': car.slug,
                'make': car.make,
                'model': car.model,
                'year': car.year,
                'price': str(car.price),
                'formatted_price': car.formatted_price,
                'mileage': car.mileage,
                'transmission': car.get_transmission_display(),
                'fuel_type': car.get_fuel_type_display(),
                'condition': car.condition,
                'image_url': image_url,
                'detail_url': car.get_absolute_url(),
            })
        
        return JsonResponse({
            'success': True,
            'category_name': category.name,
            'cars': cars_data,
            'count': len(cars_data)
        })
        
    except Category.DoesNotExist:
        return JsonResponse({'error': 'Category not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
# ✅ END NEW VIEW ✅

class CarListView(FilterView):
    """
    Filterable car listing with pagination
    OPTIMIZATION: Efficient query with select_related/prefetch_related
    OPTIMIZATION: Pagination at 12 items for mobile performance
    """
    model = Car
    filterset_class = CarFilter
    template_name = 'cars/car_list.html'
    context_object_name = 'cars'
    paginate_by = 12
    
    def get_queryset(self):
        """
        OPTIMIZATION: Reduce queries with select_related
        Images will be fetched in template only when needed
        """
        queryset = Car.objects.select_related('category')
        
        # Apply search if provided
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(make__icontains=search_query) |
                Q(model__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        
        # Add filter counts for UI
        if hasattr(self, 'object_list'):
            # Get paginated object list
            page_obj = context.get('page_obj')
            if page_obj:
                context['total_count'] = page_obj.paginator.count
            else:
                context['total_count'] = self.object_list.count()
        else:
            context['total_count'] = 0
        
        # Count applied filters
        applied_filters_count = 0
        filter_data = self.request.GET.copy()
        
        # Remove empty values and pagination parameters
        for key in list(filter_data.keys()):
            if not filter_data[key] or key in ['page', 'ordering']:
                filter_data.pop(key, None)
        
        applied_filters_count = len(filter_data)
        context['applied_filters_count'] = applied_filters_count
        
        # Add sort options for mobile modal
        context['sort_options'] = [
            ('-created_at', 'Newest First'),
            ('price', 'Price: Low to High'),
            ('-price', 'Price: High to Low'),
            ('-year', 'Year: Newest'),
            ('year', 'Year: Oldest'),
            ('mileage', 'Mileage: Low to High'),
            ('-views', 'Most Popular'),
        ]
        
        return context
    
class CarDetailView(DetailView):
    """
    Car detail page with related cars
    RATE LIMIT REMOVED FROM GET - Only apply to inquiry POST if needed
    """
    model = Car
    template_name = 'cars/car_detail.html'
    context_object_name = 'car'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_queryset(self):
        return Car.objects.select_related('category').prefetch_related('images')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        car = self.object
        
        # Increment view count
        Car.objects.filter(pk=car.pk).update(views=F('views') + 1)
        car.refresh_from_db()
        
        # Get related cars
        cache_key = f'related_cars_{car.id}'
        related_cars = cache.get(cache_key)
        
        if not related_cars:
            related_qs = Car.objects.filter(
                Q(make=car.make) | Q(category=car.category)
            ).exclude(id=car.id).select_related('category')[:4]
            
            related_cars = list(related_qs)
            
            if related_cars:
                car_ids = [c.id for c in related_cars]
                first_images = {}
                for img in CarImage.objects.filter(car_id__in=car_ids).order_by('car_id', 'order', '-is_primary'):
                    if img.car_id not in first_images:
                        first_images[img.car_id] = img
                
                for related_car in related_cars:
                    related_car.prefetched_image = first_images.get(related_car.id)
            
            cache.set(cache_key, related_cars, 60 * 30)
        
        context['related_cars'] = related_cars
        context['inquiry_form'] = CarInquiryForm()
        
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle inquiry form submission - APPLY RATE LIMIT HERE"""
        self.object = self.get_object()
        
        # Simple rate limiting check (3 submissions per 5 minutes)
        session_key = f"inquiry_submit_{request.META.get('REMOTE_ADDR')}"
        submission_count = request.session.get(session_key, 0)
        
        if submission_count >= 3:
            messages.error(
                request, 
                '🚫 Too many submissions. Please wait a few minutes before trying again.'
            )
            return redirect(self.object.get_absolute_url())
        
        form = CarInquiryForm(request.POST)
        
        if form.is_valid():
            inquiry = form.save(commit=False)
            inquiry.car = self.object
            inquiry.save()
            
            # Increment session counter
            request.session[session_key] = submission_count + 1
            request.session.set_expiry(300)  # 5 minutes
            
            messages.success(request, 'Your inquiry has been sent successfully!')
            return redirect(self.object.get_absolute_url())
        
        context = self.get_context_data()
        context['inquiry_form'] = form
        return render(request, self.template_name, context)


class CarCreateView(LoginRequiredMixin, CreateView):
    """
    Create new car listing (admin/authenticated users only)
    Handles multiple image uploads via formset
    """
    model = Car
    form_class = CarForm
    template_name = 'cars/car_form.html'
    success_url = reverse_lazy('car_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['image_formset'] = CarImageFormSet(self.request.POST, self.request.FILES)
        else:
            context['image_formset'] = CarImageFormSet()
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        image_formset = context['image_formset']
        
        if image_formset.is_valid():
            self.object = form.save()
            image_formset.instance = self.object
            image_formset.save()
            
            
            
            messages.success(self.request, 'Car listing created successfully!')
            return redirect(self.object.get_absolute_url())
        else:
            return self.render_to_response(self.get_context_data(form=form))


class CarUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update existing car listing
    """
    model = Car
    form_class = CarForm
    template_name = 'cars/car_form.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['image_formset'] = CarImageFormSet(
                self.request.POST,
                self.request.FILES,
                instance=self.object
            )
        else:
            context['image_formset'] = CarImageFormSet(instance=self.object)
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        image_formset = context['image_formset']
        
        if image_formset.is_valid():
            self.object = form.save()
            image_formset.instance = self.object
            image_formset.save()
            
            
            
            messages.success(self.request, 'Car listing updated successfully!')
            return redirect(self.object.get_absolute_url())
        else:
            return self.render_to_response(self.get_context_data(form=form))


class CarDeleteView(LoginRequiredMixin, DeleteView):
    """
    Delete car listing
    """
    model = Car
    template_name = 'cars/car_confirm_delete.html'
    success_url = reverse_lazy('car_list')
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def delete(self, request, *args, **kwargs):
        car = self.get_object()
        
        
        
        messages.success(request, 'Car listing deleted successfully!')
        return super().delete(request, *args, **kwargs)


class CategoryListView(ListView):
    """
    List cars by category
    """
    model = Car
    template_name = 'cars/category_list.html'
    context_object_name = 'cars'
    paginate_by = 12
    
    def get_queryset(self):
        category_slug = self.kwargs.get('slug')
        return Car.objects.filter(
            category__slug=category_slug
        ).select_related('category')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category_slug = self.kwargs.get('slug')
        context['category'] = get_object_or_404(Category, slug=category_slug)
        return context


class SectionListView(ListView):
    """
    List cars by section (sweet_deals, foreign_used, etc.)
    NO FEATURED FIELD - Only uses section and condition fields
    """
    model = Car
    template_name = 'cars/section_list.html'
    context_object_name = 'cars'
    paginate_by = 12
    
    def get_queryset(self):
        section = self.kwargs.get('section')
        
        # Build query based on section
        if section == 'sweet_deals':
            # Only cars with section='sweet_deals'
            queryset = Car.objects.filter(section='sweet_deals')
        elif section == 'foreign_used':
            # section='foreign_used' OR condition='foreign_used'
            queryset = Car.objects.filter(Q(section='foreign_used') | Q(condition='foreign_used'))
        elif section == 'local_used':
            # section='local_used' OR condition='local_used'
            queryset = Car.objects.filter(Q(section='local_used') | Q(condition='local_used'))
        elif section == 'new_cars':
            # section='new_cars' OR condition='new'
            queryset = Car.objects.filter(Q(section='new_cars') | Q(condition='new'))
        elif section == 'latest_listings':
            # Just get latest cars, no section filter
            queryset = Car.objects.all()
        else:
            # Fallback: filter by section value
            queryset = Car.objects.filter(section=section)
        
        return queryset.select_related('category').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        section = self.kwargs.get('section')
        
        # Human-readable section names
        section_names = {
            'sweet_deals': 'Sweet Deals',
            'foreign_used': 'Foreign Used Cars',
            'local_used': 'Locally Used Cars',
            'new_cars': 'Brand New Cars',
            'latest_listings': 'Latest Listings',
        }
        
        context['section_name'] = section_names.get(section, section.replace('_', ' ').title())
        context['section'] = section
        return context
    
def about_view(request):
    return render(request, 'cars/about.html')

def contact_view(request):
    return render(request, 'cars/contact.html')


# ========================================
# STEP 1: Show Interest (Convert Inquiry to Booking)
# ========================================

@require_http_methods(["POST"])
def create_booking_from_inquiry(request):
    """
    Create booking directly from inquiry form on car detail page
    This is called when customer submits inquiry and wants to start booking
    """
    car_id = request.POST.get('car_id')
    name = request.POST.get('name')
    phone = request.POST.get('phone')
    email = request.POST.get('email', '')
    message = request.POST.get('message', '')
    
    if not all([car_id, name, phone]):
        messages.error(request, 'Please fill in all required fields.')
        return redirect('car_list')
    
    try:
        car = Car.objects.get(id=car_id)
    except Car.DoesNotExist:
        messages.error(request, 'Car not found.')
        return redirect('car_list')
    
    # Check if car is sold
    if car.is_sold:
        messages.error(request, 'Sorry, this car has been sold.')
        return redirect('car_detail', slug=car.slug)
    
    # Create inquiry first
    inquiry = CarInquiry.objects.create(
        car=car,
        name=name,
        phone=phone,
        email=email,
        message=message or f"I'm interested in {car.title}"
    )
    
    # Create booking from inquiry
    booking = CarBooking.objects.create(
        inquiry=inquiry,
        car=car,
        customer_name=name,
        customer_phone=phone,
        customer_email=email,
        status='interest_shown'
    )
    
    # Mark inquiry as converted
    inquiry.converted_to_booking = True
    inquiry.save()
    
    # Create initial activity
    BookingActivity.objects.create(
        booking=booking,
        activity_type='status_change',
        title='🎉 Booking Created',
        description=f'{name} started the booking journey for {car.title}',
        performed_by='Customer',
        is_visible_to_customer=True
    )
    
    # Initial welcome message
    BookingMessage.objects.create(
        booking=booking,
        message=f"""Welcome to your booking journey! 🚗

Here's what happens next:

1️⃣ **Schedule Inspection** - Pick a time to view the car
2️⃣ **Negotiate Price** - Chat with us to get the best deal
3️⃣ **Schedule Payment** - Choose when to make payment
4️⃣ **Complete Purchase** - Collect documents & FREE 5L Engine Oil! 🎁

You can message us anytime using the chat. We typically respond within 30 minutes during business hours.

Let's get started! 🎉""",
        is_from_admin=True
    )
    
    messages.success(
        request,
        f'🎉 Booking #{booking.id} created! You can now schedule inspection and negotiate in the app.'
    )
    
    return redirect('booking_detail', booking_id=booking.id)


# ========================================
# STEP 2: Booking Detail Page (Main Hub)
# ========================================
@require_http_methods(["GET", "POST"])
def booking_detail(request, booking_id):
    """
    Main booking page - shows progress, messages, and actions
    Customer can see everything happening in real-time
    """
    booking = get_object_or_404(CarBooking, id=booking_id, is_active=True)
    
    # Handle customer sending message
    if request.method == 'POST':
        message_text = request.POST.get('message', '').strip()
        price_offer = request.POST.get('price_offer', '').strip()
        
        if message_text:
            # Create message
            msg = BookingMessage.objects.create(
                booking=booking,
                message=message_text,
                is_from_admin=False,
                price_offer=float(price_offer) if price_offer else None
            )
            
            # Create activity
            activity_title = 'New message from customer'
            if price_offer:
                activity_title = f'Customer offered ₦{float(price_offer):,.0f}'
            
            BookingActivity.objects.create(
                booking=booking,
                activity_type='message',
                title=activity_title,
                description=message_text[:100],
                performed_by='Customer',
                is_visible_to_customer=True
            )
            
           # messages.success(request, 'Message sent! We\'ll respond shortly.')
            return redirect('booking_detail', booking_id=booking.id)
    
    # Get all messages
    booking_messages = booking.messages.all()
    
    # Mark admin messages as read by customer
    booking.messages.filter(is_from_admin=True, is_read=False).update(
        is_read=True,
        read_at=timezone.now()
    )
    
    # Get activities (timeline)
    activities = booking.activities.filter(is_visible_to_customer=True)
    
    # Calculate progress
    progress = booking.progress_percentage
    
    # Next actions based on status
    next_actions = {
        'interest_shown': {
            'title': 'Schedule Inspection',
            'description': 'Pick a date and time to inspect the car',
            'button_text': 'Schedule Now',
            'button_url': f'/booking/{booking.id}/schedule-inspection/',
            'can_do': True
        },
        'inspection_scheduled': {
            'title': 'Attend Inspection',
            'description': f'Inspection on {booking.inspection_date.strftime("%B %d at %I:%M %p") if booking.inspection_date else "TBD"}',
            'button_text': 'View Details',
            'button_url': '#',
            'can_do': False
        },
        'payment_scheduled': {
            'title': 'Make Payment',
            'description': f'Payment due: {booking.payment_scheduled_date.strftime("%B %d, %Y") if booking.payment_scheduled_date else "TBD"}',
            'button_text': 'Contact for Payment Details',
            'button_url': '#chat',
            'can_do': True
        },
        'payment_confirmed': {
            'title': 'Collect Documents',
            'description': 'Visit showroom to collect car documents and free gift',
            'button_text': 'Get Directions',
            'button_url': '#',
            'can_do': True
        },
        'completed': {
            'title': '🎉 Congratulations!',
            'description': 'Enjoy your new car!',
            'button_text': None,
            'button_url': None,
            'can_do': False
        }
    }
    
    context = {
        'booking': booking,
        'car': booking.car,
        'messages': booking_messages,
        'activities': activities,
        'progress': progress,
        'next_action': next_actions.get(booking.status, {}),
        'show_free_gift_banner': booking.status not in ['completed', 'cancelled'],
    }
    
    return render(request, 'cars/booking_detail.html', context)


# ========================================
# STEP 3: Schedule Inspection
# ========================================
@require_http_methods(["GET", "POST"])
def schedule_inspection(request, booking_id):
    """Customer schedules inspection"""
    booking = get_object_or_404(CarBooking, id=booking_id, is_active=True)
    
    if booking.status != 'interest_shown':
        messages.info(request, 'Inspection already scheduled or booking in later stage.')
        return redirect('booking_detail', booking_id=booking.id)
    
    if request.method == 'POST':
        inspection_date = request.POST.get('inspection_date')
        inspection_time = request.POST.get('inspection_time')
        inspection_location = request.POST.get('inspection_location')
        
        # Combine date and time
        from datetime import datetime
        dt_str = f"{inspection_date} {inspection_time}"
        dt_obj = datetime.strptime(dt_str, '%Y-%m-%d %H:%M')
        
        # Update booking
        booking.inspection_date = dt_obj
        booking.inspection_location = inspection_location
        booking.status = 'inspection_scheduled'
        booking.save()
        
        # Create activity
        BookingActivity.objects.create(
            booking=booking,
            activity_type='inspection',
            title='📅 Inspection Scheduled',
            description=f'Inspection scheduled for {dt_obj.strftime("%B %d, %Y at %I:%M %p")} at {inspection_location}',
            performed_by='Customer',
            is_visible_to_customer=True
        )
        
        # Send confirmation message
        BookingMessage.objects.create(
            booking=booking,
            message=f"""✅ Inspection confirmed!

**Date:** {dt_obj.strftime("%B %d, %Y")}
**Time:** {dt_obj.strftime("%I:%M %p")}
**Location:** {inspection_location}

We'll send you a reminder 24 hours before. See you then! 🚗""",
            is_from_admin=True
        )
        
        messages.success(request, f'✅ Inspection scheduled for {dt_obj.strftime("%B %d at %I:%M %p")}!')
        return redirect('booking_detail', booking_id=booking.id)
    
    context = {
        'booking': booking,
        'car': booking.car
    }
    return render(request, 'cars/schedule_inspection.html', context)


# ========================================
# STEP 4: Schedule Payment
# ========================================
@require_http_methods(["GET", "POST"])
def schedule_payment(request, booking_id):
    """Customer schedules payment after inspection"""
    booking = get_object_or_404(CarBooking, id=booking_id, is_active=True)
    
    if booking.status != 'inspection_scheduled':
        messages.info(request, 'Please complete inspection first.')
        return redirect('booking_detail', booking_id=booking.id)
    
    if request.method == 'POST':
        payment_date = request.POST.get('payment_date')
        payment_method = request.POST.get('payment_method')
        
        booking.payment_scheduled_date = payment_date
        booking.payment_method = payment_method
        booking.status = 'payment_scheduled'
        booking.save()
        
        # Create activity
        BookingActivity.objects.create(
            booking=booking,
            activity_type='payment',
            title='💰 Payment Date Scheduled',
            description=f'Payment scheduled for {payment_date} via {booking.get_payment_method_display()}',
            performed_by='Customer',
            is_visible_to_customer=True
        )
        
        # Send payment details message
        BookingMessage.objects.create(
            booking=booking,
            message=f"""✅ Payment scheduled for {payment_date}!

**Final Price:** {booking.formatted_final_price}
**Method:** {booking.get_payment_method_display()}

**Bank Details:**
Bank: GTBank
Account: 0123456789
Name: Enoriel Growth Ltd

Send payment confirmation screenshot here after payment.

🎁 **Don't forget:** You'll receive 5L Engine Oil as a FREE gift when you complete payment!""",
            is_from_admin=True
        )
        
        messages.success(request, f'✅ Payment scheduled! We\'ve sent payment details to your booking chat.')
        return redirect('booking_detail', booking_id=booking.id)
    
    context = {
        'booking': booking,
        'car': booking.car
    }
    return render(request, 'cars/schedule_payment.html', context)


# ========================================
# API: Real-time Updates
# ========================================
@require_http_methods(["GET"])
def booking_updates_api(request, booking_id):
    """
    API for polling new messages and status updates
    Called every 10 seconds by frontend
    """
    try:
        booking = CarBooking.objects.get(id=booking_id, is_active=True)

        # Get last message timestamp from query param
        last_check = request.GET.get('last_check')

        last_check_dt = None
        if last_check:
            last_check_dt = parse_datetime(last_check)

        # Fallback if parsing fails
        if last_check_dt is None:
            last_check_dt = booking.updated_at

        new_messages = booking.messages.filter(
            created_at__gt=last_check_dt
        ).count()

        return JsonResponse({
            'success': True,
            'booking_id': booking.id,
            'status': booking.status,
            'status_display': booking.get_status_display(),
            'progress': booking.progress_percentage,
            'new_messages': new_messages,
            'unread_count': booking.messages.filter(
                is_from_admin=True,
                is_read=False
            ).count(),
            'updated_at': booking.updated_at.isoformat(),
        })

    except CarBooking.DoesNotExist:
        return JsonResponse(
            {'success': False, 'error': 'Booking not found'},
            status=404
        )



@require_http_methods(["GET", "POST"])
def my_bookings(request):
    """
    Customer can view their bookings by phone/email
    No authentication needed
    """
    bookings = []
    search_performed = False
    
    if request.method == 'POST' or request.GET.get('phone') or request.GET.get('email'):
        phone = request.POST.get('phone', '') or request.GET.get('phone', '')
        email = request.POST.get('email', '') or request.GET.get('email', '')
        
        phone = phone.strip()
        email = email.strip()
        
        if phone or email:
            search_performed = True
            query = Q()
            if phone:
                # Clean phone number for search
                clean_phone = phone.replace(' ', '').replace('-', '').replace('+', '')
                query |= Q(customer_phone__icontains=clean_phone)
            if email:
                query |= Q(customer_email__iexact=email)
            
            bookings = CarBooking.objects.filter(query).select_related('car').order_by('-created_at')
    
    context = {
        'bookings': bookings,
        'search_phone': request.POST.get('phone', '') or request.GET.get('phone', ''),
        'search_email': request.POST.get('email', '') or request.GET.get('email', ''),
        'search_performed': search_performed,
    }
    
    return render(request, 'cars/my_bookings.html', context)
