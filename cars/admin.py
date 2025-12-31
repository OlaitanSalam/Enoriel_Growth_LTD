from django.contrib import admin
from django.utils.html import format_html
from .models import Car, CarImage, Category, CarInquiry, SoldCar, CarBooking, BookingMessage, BookingActivity
from .forms import CarForm
from django.utils import timezone
from django.shortcuts import redirect


class CarImageInline(admin.TabularInline):
    """
    Inline admin for car images
    """
    model = CarImage
    extra = 3
    fields = ['image', 'alt_text', 'is_primary', 'image_preview']
    readonly_fields = ['image_preview']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 100px;" />', obj.image.url)
        return "No image"
    image_preview.short_description = 'Preview'


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for Car model
    """
    form = CarForm
    list_display = [
        'thumbnail', 'title', 'make', 'model', 'year', 'section',
        'formatted_price_display', 'condition',  
        'views', 'created_at'
    ]
    list_filter = [
        'condition', 'make', 'transmission', 'fuel_type', 'section',
         'created_at'
    ]
    search_fields = ['title', 'make', 'model', 'description', 'slug', 'section']
    list_per_page = 25
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'make', 'model', 'year', 'category')
        }),
        ('Pricing & Specs', {
            'fields': ('price', 'condition', 'mileage', 'transmission', 'fuel_type', 'car_interior', 'engine_type')
        }),
        ('Description', {
            'fields': ('description',)
        }),

        ('Status', {
            'fields': ('is_sold',),
            'description': 'Mark as sold to show blur effect on frontend. Use SoldCar model to record sale details.'
        }),
        ('Additional Details', {
            'fields': ('location', 'color', 'section'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('views', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'views',]
    inlines = [CarImageInline]
    
    def thumbnail(self, obj):
        """Display thumbnail in list view"""
        main_image = obj.main_image
        if main_image:
            return format_html(
                '<img src="{}" style="width: 80px; height: 60px; object-fit: cover; border-radius: 4px;" />',
                main_image.image.url
            )
        return "No image"
    thumbnail.short_description = 'Image'
    
    def formatted_price_display(self, obj):
        """Display formatted price"""
        return obj.formatted_price
    formatted_price_display.short_description = 'Price'
    formatted_price_display.admin_order_field = 'price'

    def sold_status(self, obj):
        """Display sold status with visual indicator"""
        if obj.is_sold:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;">SOLD</span>'
            )
        return format_html(
            '<span style="background-color: #28a745; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;">AVAILABLE</span>'
        )
    sold_status.short_description = 'Status'
    
    actions = ['mark_as_featured', 'unmark_as_featured', 'mark_as_sold', 'mark_as_available']
    
    def mark_as_featured(self, request, queryset):
        """Bulk action to mark cars as featured"""
        updated = queryset.update(featured=True)
        self.message_user(request, f'{updated} cars marked as featured.')
    mark_as_featured.short_description = 'Mark selected cars as featured'
    
    def unmark_as_featured(self, request, queryset):
        """Bulk action to unmark cars as featured"""
        updated = queryset.update(featured=False)
        self.message_user(request, f'{updated} cars unmarked as featured.')
    unmark_as_featured.short_description = 'Unmark selected cars as featured'

    def mark_as_sold(self, request, queryset):
        """Bulk action to mark cars as sold"""
        updated = queryset.update(is_sold=True)
        self.message_user(request, f'{updated} cars marked as sold.')
    mark_as_sold.short_description = 'Mark selected cars as sold'
    
    def mark_as_available(self, request, queryset):
        """Bulk action to mark cars as available"""
        updated = queryset.update(is_sold=False)
        self.message_user(request, f'{updated} cars marked as available.')
    mark_as_available.short_description = 'Mark selected cars as available'


@admin.register(SoldCar)
class SoldCarAdmin(admin.ModelAdmin):
    """
    Admin interface for Sold Cars with searchable car selection
    """
    list_display = [
        'car_thumbnail', 'car_details', 'original_price', 'formatted_final_price_display',
        'profit_display', 'buyer_name', 'sold_date'
    ]
    list_filter = ['sold_date']
    search_fields = [
        'car__title', 'car__make', 'car__model', 'car__slug',
        'buyer_name', 'buyer_phone', 'buyer_email', 'description'
    ]
    date_hierarchy = 'sold_date'
    readonly_fields = ['sold_date', 'profit_margin', 'formatted_profit']
    list_per_page = 25
    
    # CRUCIAL: This enables the searchable dropdown for the car field
    autocomplete_fields = ['car']
    
    fieldsets = (
        ('Car Information', {
            'fields': ('car',),
            'description': 'Search for the car by make, model, or title. Type to filter from 500+ cars.'
        }),
        ('Sale Details', {
            'fields': ('final_price', 'profit_margin', 'sold_date')
        }),
        ('Buyer Information', {
            'fields': ('buyer_name', 'buyer_phone', 'buyer_email'),
            'classes': ('collapse',)
        }),
        ('Additional Notes', {
            'fields': ('description',),
            'classes': ('collapse',)
        }),
    )
    
    def car_thumbnail(self, obj):
        """Display car thumbnail"""
        main_image = obj.car.main_image
        if main_image:
            return format_html(
                '<img src="{}" style="width: 80px; height: 60px; object-fit: cover; border-radius: 4px;" />',
                main_image.image.url
            )
        return "No image"
    car_thumbnail.short_description = 'Image'
    
    def car_details(self, obj):
        """Display car details with link"""
        return format_html(
            '<strong>{}</strong><br><small>{} {} {}</small>',
            obj.car.title,
            obj.car.year,
            obj.car.make,
            obj.car.model
        )
    car_details.short_description = 'Car'
    
    def original_price(self, obj):
        """Display original listing price"""
        return obj.car.formatted_price
    original_price.short_description = 'Original Price'
    
    def formatted_final_price_display(self, obj):
        """Display final sale price"""
        return obj.formatted_final_price
    formatted_final_price_display.short_description = 'Final Price'
    formatted_final_price_display.admin_order_field = 'final_price'
    
    def profit_display(self, obj):
        """Display profit with color coding"""
        if obj.profit_margin:
            color = '#28a745' if obj.profit_margin >= 0 else '#dc3545'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color,
                obj.formatted_profit
            )
        return 'N/A'
    profit_display.short_description = 'Profit'
    profit_display.admin_order_field = 'profit_margin'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    Admin interface for Category model
    """
    list_display = ['name', 'slug', 'car_count', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    
    def car_count(self, obj):
        """Show number of cars in category"""
        return obj.cars.count()
    car_count.short_description = 'Number of Cars'


@admin.register(CarImage)
class CarImageAdmin(admin.ModelAdmin):
    """
    Admin interface for CarImage model
    """
    list_display = ['image_preview', 'car', 'is_primary', 'uploaded_at']
    list_filter = ['is_primary', 'uploaded_at']
    search_fields = ['car__title', 'alt_text']
    list_per_page = 50
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 80px;" />', obj.image.url)
        return "No image"
    image_preview.short_description = 'Preview'


@admin.register(CarInquiry)
class CarInquiryAdmin(admin.ModelAdmin):
    """
    Admin interface for car inquiries
    """
    list_display = ['car', 'name', 'email', 'phone', 'contacted', 'created_at']
    list_filter = ['contacted', 'created_at']
    search_fields = ['name', 'email', 'phone', 'car__title']
    list_editable = ['contacted']
    readonly_fields = ['car', 'name', 'email', 'phone', 'message', 'created_at']
    date_hierarchy = 'created_at'
    list_per_page = 50
    
    fieldsets = (
        ('Inquiry Details', {
            'fields': ('car', 'name', 'email', 'phone')
        }),
        ('Message', {
            'fields': ('message',)
        }),
        ('Status', {
            'fields': ('contacted', 'created_at', 'converted_to_booking')
        }),
    )
    
    actions = ['mark_as_contacted']
    
    def mark_as_contacted(self, request, queryset):
        """Bulk action to mark inquiries as contacted"""
        updated = queryset.update(contacted=True)
        self.message_user(request, f'{updated} inquiries marked as contacted.')
    mark_as_contacted.short_description = 'Mark as contacted'



class BookingMessageInline(admin.TabularInline):
    """Show recent messages in booking admin"""
    model = BookingMessage
    extra = 1
    fields = ['message', 'is_from_admin', 'price_offer', 'created_at']
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by('-created_at')


class BookingActivityInline(admin.TabularInline):
    """Show activities in booking admin"""
    model = BookingActivity
    extra = 0
    fields = ['title', 'activity_type', 'performed_by', 'created_at']
    readonly_fields = ['created_at']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(CarBooking)
class CarBookingAdmin(admin.ModelAdmin):
    """
    Complete booking management with in-app messaging
    """
    list_display = [
        'booking_id', 'car_thumbnail', 'customer_info', 
        'status_badge', 'progress_bar', 'price_info',
        'unread_indicator', 'created_at'
    ]
    list_filter = ['status', 'is_active', 'free_gift_claimed', 'created_at']
    search_fields = [
        'customer_name', 'customer_phone', 'customer_email',
        'car__title', 'car__make', 'car__model'
    ]
    date_hierarchy = 'created_at'
    list_per_page = 25
    
    autocomplete_fields = ['car']
    
    fieldsets = (
        ('Booking Information', {
            'fields': ('car', 'inquiry', 'status', 'is_active')
        }),
        ('Customer Details', {
            'fields': ('customer_name', 'customer_phone', 'customer_email', 'notify_by_email')
        }),
        ('Inspection Details', {
            'fields': ('inspection_date', 'inspection_location', 'inspection_notes'),
            'classes': ('collapse',)
        }),
        ('Payment Details', {
            'fields': (
                'negotiated_price', 'payment_scheduled_date', 'payment_method',
                'payment_confirmed_date', 'payment_reference'
            ),
            'classes': ('collapse',)
        }),
        ('Free Gift', {
            'fields': ('free_gift_claimed', 'free_gift_claimed_date'),
            'classes': ('collapse',)
        }),
        ('Admin Notes', {
            'fields': ('admin_notes',),
            'description': 'Internal notes - not visible to customer'
        }),
        ('Message Timestamps', {
            'fields': ('last_customer_message', 'last_admin_response'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'last_customer_message', 'last_admin_response']
    inlines = [BookingMessageInline, BookingActivityInline]
    
    actions = [
        'send_message_to_selected',
        'advance_to_inspection',
        'advance_to_payment',
        'confirm_payment',
        'mark_completed',
        'cancel_bookings'
    ]
    
    def booking_id(self, obj):
        return format_html(
            '<a href="/Enoriel-administrator/cars/carbooking/{}/change/" style="font-weight: bold;">#{}</a>',
            obj.id, obj.id
        )
    booking_id.short_description = 'ID'
    
    def car_thumbnail(self, obj):
        main_image = obj.car.main_image
        if main_image:
            return format_html(
                '<img src="{}" style="width: 60px; height: 45px; object-fit: cover; border-radius: 4px;" />',
                main_image.image.url
            )
        return "No image"
    car_thumbnail.short_description = 'Car'
    
    def customer_info(self, obj):
        return format_html(
            '<strong>{}</strong><br><small>📞 {}</small>',
            obj.customer_name,
            obj.customer_phone
        )
    customer_info.short_description = 'Customer'
    
    def status_badge(self, obj):
        colors = {
            'interest_shown': '#6c757d',
            'inspection_scheduled': '#007bff',
            'payment_scheduled': '#ffc107',
            'payment_confirmed': '#28a745',
            'completed': '#17a2b8',
            'cancelled': '#dc3545',
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 10px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def progress_bar(self, obj):
        percent = obj.progress_percentage
        color = '#28a745' if percent == 100 else '#007bff'
        return format_html(
            '<div style="width: 100px; background: #e9ecef; border-radius: 10px; height: 8px;">'
            '<div style="width: {}%; background: {}; height: 100%; border-radius: 10px;"></div>'
            '</div><small style="font-size: 10px; color: #666;">{}%</small>',
            percent, color, percent
        )
    progress_bar.short_description = 'Progress'
    
    def price_info(self, obj):
        if obj.negotiated_price:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">{}</span><br>'
                '<small style="text-decoration: line-through; color: #999;">{}</small>',
                obj.formatted_final_price,
                obj.car.formatted_price
            )
        return obj.car.formatted_price
    price_info.short_description = 'Price'
    
    def unread_indicator(self, obj):
        unread = obj.unread_count_for_admin
        if unread > 0:
            return format_html(
                '<span style="background: #dc3545; color: white; padding: 2px 8px; '
                'border-radius: 10px; font-size: 11px; font-weight: bold;">{} new</span>',
                unread
            )
        return format_html('<span style="color: #28a745;">✓ Read</span>')
    unread_indicator.short_description = '💬 Messages'
    
    # Bulk Actions
    def send_message_to_selected(self, request, queryset):
        """Open page to send message to selected bookings"""
        selected = queryset.values_list('id', flat=True)
        return redirect(f'/Enoriel-administrator/send-bulk-message/?ids={",".join(map(str, selected))}')
    send_message_to_selected.short_description = '💬 Send Message to Selected'
    
    def advance_to_inspection(self, request, queryset):
        updated = 0
        for booking in queryset.filter(status='interest_shown'):
            booking.status = 'inspection_scheduled'
            booking.save()
            
            BookingActivity.objects.create(
                booking=booking,
                activity_type='status_change',
                title='Status updated by Admin',
                description='Moved to inspection stage',
                performed_by='Admin',
                is_visible_to_customer=True
            )
            updated += 1
        
        self.message_user(request, f'{updated} bookings moved to inspection stage.')
    advance_to_inspection.short_description = '📅 Move to Inspection'
    
    def confirm_payment(self, request, queryset):
        updated = 0
        for booking in queryset.filter(status='payment_scheduled'):
            booking.status = 'payment_confirmed'
            booking.payment_confirmed_date = timezone.now()
            booking.save()
            
            BookingMessage.objects.create(
                booking=booking,
                message='✅ Payment confirmed! Visit our showroom to collect documents and your free 5L Engine Oil gift. Congratulations! 🎉',
                is_from_admin=True
            )
            
            BookingActivity.objects.create(
                booking=booking,
                activity_type='payment',
                title='✅ Payment Confirmed',
                description='Admin confirmed payment received',
                performed_by='Admin',
                is_visible_to_customer=True
            )
            updated += 1
        
        self.message_user(request, f'{updated} payments confirmed.')
    confirm_payment.short_description = '✅ Confirm Payment'
    
    def mark_completed(self, request, queryset):
        updated = 0
        for booking in queryset.filter(status='payment_confirmed'):
            booking.status = 'completed'
            if not booking.free_gift_claimed:
                booking.free_gift_claimed = True
                booking.free_gift_claimed_date = timezone.now()
            booking.save()
            
            BookingActivity.objects.create(
                booking=booking,
                activity_type='status_change',
                title='🎉 Purchase Completed',
                description='Booking completed successfully',
                performed_by='Admin',
                is_visible_to_customer=True
            )
            updated += 1
        
        self.message_user(request, f'{updated} bookings marked as completed.')
    mark_completed.short_description = '🎉 Mark as Completed'
    
    def cancel_bookings(self, request, queryset):
        updated = queryset.exclude(status__in=['completed', 'cancelled']).update(
            status='cancelled',
            is_active=False
        )
        self.message_user(request, f'{updated} bookings cancelled.')
    cancel_bookings.short_description = '❌ Cancel Bookings'


@admin.register(BookingMessage)
class BookingMessageAdmin(admin.ModelAdmin):
    """Manage all booking messages"""
    list_display = ['booking_id', 'sender', 'message_preview', 'price_offer_display', 'is_read', 'created_at']
    list_filter = ['is_from_admin', 'is_read', 'created_at']
    search_fields = ['booking__customer_name', 'booking__customer_phone', 'message']
    date_hierarchy = 'created_at'
    readonly_fields = ['booking', 'created_at', 'read_at']
    
    fieldsets = (
        ('Message Details', {
            'fields': ('booking', 'message', 'is_from_admin', 'price_offer', 'attachment')
        }),
        ('Read Status', {
            'fields': ('is_read', 'read_at', 'created_at')
        }),
    )
    
    def booking_id(self, obj):
        return f"#{obj.booking.id}"
    booking_id.short_description = 'Booking'
    
    def sender(self, obj):
        if obj.is_from_admin:
            return format_html('<span style="color: #007bff; font-weight: bold;">👨‍💼 Admin</span>')
        return format_html('<span style="color: #28a745;">👤 {}</span>', obj.booking.customer_name)
    sender.short_description = 'From'
    
    def message_preview(self, obj):
        preview = obj.message[:80] + '...' if len(obj.message) > 80 else obj.message
        return preview
    message_preview.short_description = 'Message'
    
    def price_offer_display(self, obj):
        if obj.price_offer:
            return format_html(
                '<strong style="color: #28a745;">₦{}</strong>',
                format(obj.price_offer, ',.0f')
            )
        return '-'



@admin.register(BookingActivity)
class BookingActivityAdmin(admin.ModelAdmin):
    """View all booking activities"""
    list_display = ['booking_id', 'customer_name', 'activity_type', 'title', 'performed_by', 'created_at']
    list_filter = ['activity_type', 'performed_by', 'is_visible_to_customer', 'created_at']
    search_fields = ['booking__customer_name', 'title', 'description']
    date_hierarchy = 'created_at'
    readonly_fields = ['booking', 'created_at']
    
    def booking_id(self, obj):
        return f"#{obj.booking.id}"
    booking_id.short_description = 'Booking'
    
    def customer_name(self, obj):
        return obj.booking.customer_name
    customer_name.short_description = 'Customer'