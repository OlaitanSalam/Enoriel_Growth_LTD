from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys
from datetime import datetime
from django.core.exceptions import ValidationError
from django.utils import timezone

# Transmission choices
TRANSMISSION_CHOICES = [
    ('automatic', 'Automatic'),
    ('manual', 'Manual'),
]

# Fuel type choices
FUEL_TYPE_CHOICES = [
    ('petrol', 'Petrol'),
    ('diesel', 'Diesel'),
    ('electric', 'Electric'),
    ('hybrid', 'Hybrid'),
]

# Nigerian market condition types
CONDITION_CHOICES = [
    ('new', 'Brand New'),
    ('foreign_used', 'Foreign Used'),
    ('local_used', 'Locally Used'),
]

# Section choices for display groups (e.g., for homepage sections)
SECTION_CHOICES = [
    ('sweet_deals', 'Sweet Deals'),
    ('latest_listings', 'Latest Listings'),
    ('featured', 'Featured'),
    # Add more as needed, but note: some like 'latest' can be dynamic via queries
]

# Booking Status Choices
BOOKING_STATUS_CHOICES = [
    ('interest_shown', '1️⃣ Interest Shown'),
    ('inspection_scheduled', '2️⃣ Inspection Scheduled'),
    ('payment_scheduled', '3️⃣ Payment Scheduled'),
    ('payment_confirmed', '4️⃣ Payment Confirmed'),
    ('completed', '✅ Completed'),
    ('cancelled', '❌ Cancelled'),
]

class Category(models.Model):
    """
    Categories for car types (e.g., Sedan, SUV, Truck, Coupe)
    This is separate from sections, which are for display groups.
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('category_list', kwargs={'slug': self.slug})

class Car(models.Model):
    """
    Main Car model with Nigerian market optimizations
    Indexes on frequently filtered fields for query speed
    Make is now a free-text CharField without hardcoded choices for flexibility.
    Added section as a choice field for display groups like 'Sweet Deals'.
    Note: For dynamic sections like 'Latest Listings', use queries (e.g., order by created_at).
    Featured flag retained for additional highlighting.
    """
    # Basic Information
    title = models.CharField(max_length=200, help_text="e.g., 2020 Toyota Corolla LE")
    make = models.CharField(max_length=100, db_index=True)  # Free input, no choices
    model = models.CharField(max_length=100, db_index=True)
    year = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1940),
            MaxValueValidator(datetime.now().year + 1)
        ],
        db_index=True
    )
   
    # Pricing - Using DecimalField for precision
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Price in Nigerian Naira (NGN)",
        db_index=True  # Index for price range queries
    )
   
    # Vehicle Details
    mileage = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Mileage in kilometers",
        db_index=True
    )
    transmission = models.CharField(
        max_length=20,
        choices=TRANSMISSION_CHOICES,
        default='automatic',
        db_index=True
    )
    fuel_type = models.CharField(
        max_length=20,
        choices=FUEL_TYPE_CHOICES,
        default='petrol',
        db_index=True
    )
    car_interior = models.CharField(max_length=100, blank=True, help_text="Interior type, e.g., Leather, Fabric")
    engine_type = models.CharField(max_length=100, blank=True, help_text="Engine type, e.g., V6, I4")
    condition = models.CharField(
        max_length=20,
        choices=CONDITION_CHOICES,
        db_index=True  # Critical filter for Nigerian market
    )
   
    # Additional Information
    description = models.TextField(help_text="Detailed description of the car")
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name='cars'
    )
    section = models.CharField(
        max_length=50,
        choices=SECTION_CHOICES,
        blank=True,
        help_text="Assign to a display section (can be blank; use queries for dynamic)"
    )
   
    is_sold = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Mark this car as sold (will show blur effect on frontend)"
    )
   
    # Features
    featured = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Highlight as featured (e.g., in Sweet Deals)"
    )
   
    # SEO and URL
    slug = models.SlugField(max_length=250, unique=True, blank=True)
   
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    views = models.PositiveIntegerField(default=0)  # Track popularity
   
    # Optional fields for Nigerian market
    location = models.CharField(max_length=100, blank=True, help_text="e.g., Lagos, Abuja")
    color = models.CharField(max_length=50, blank=True)
   
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['make', 'model']),
            models.Index(fields=['condition', 'price']),
            models.Index(fields=['featured', '-created_at']),
            models.Index(fields=['section']),
            models.Index(fields=['is_sold']),
        ]
        verbose_name = "Car"
        verbose_name_plural = "Cars"

    def __str__(self):
        return f"{self.year} {self.make} {self.model}"

    def save(self, *args, **kwargs):
        """
        Override save to auto-generate slug
        Format: year-make-model-random for uniqueness
        """
        if not self.slug:
            base_slug = slugify(f"{self.year} {self.make} {self.model}")
            slug = base_slug
            counter = 1
            # Ensure unique slug
            while Car.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('car_detail', kwargs={'slug': self.slug})

    @property
    def formatted_price(self):
        """Format price in Nigerian Naira"""
        return f"₦{self.price:,.0f}"

    @property
    def main_image(self):
        """Get the first image or None"""
        return self.images.first()
    

class SoldCar(models.Model):
    """
    Record keeping for sold cars with final negotiated price and sale details
    """
    car = models.OneToOneField(
        Car,
        on_delete=models.CASCADE,
        related_name='sold_record',
        help_text="Select the car that was sold"
    )
    final_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Final negotiated price in Nigerian Naira (NGN)"
    )
    sold_date = models.DateTimeField(
        auto_now_add=True,
        help_text="Date and time when the car was sold"
    )
    buyer_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Name of the buyer (optional)"
    )
    buyer_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text="Buyer's phone number (optional)"
    )
    buyer_email = models.EmailField(
        blank=True,
        help_text="Buyer's email (optional)"
    )
    description = models.TextField(
        blank=True,
        help_text="Additional notes about the sale, negotiation details, etc."
    )
    profit_margin = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Profit made on this sale (calculated automatically if listing price is available)"
    )
    
    class Meta:
        ordering = ['-sold_date']
        verbose_name = "Sold Car Record"
        verbose_name_plural = "Sold Cars Records"
    
    def __str__(self):
        return f"Sold: {self.car.title} - {self.formatted_final_price}"
    
    @property
    def formatted_final_price(self):
        return f"₦{self.final_price:,.0f}"
    
    @property
    def formatted_profit(self):
        if self.profit_margin:
            return f"₦{self.profit_margin:,.0f}"
        return "N/A"
    
    def save(self, *args, **kwargs):
        # Auto-calculate profit margin
        if self.car and self.car.price:
            self.profit_margin = self.final_price - self.car.price
        
        # Automatically mark the car as sold
        if self.car:
            self.car.is_sold = True
            self.car.save()
        
        super().save(*args, **kwargs)

class CarImage(models.Model):
    """
    Multiple images per car with automatic optimization
    Images compressed to WebP format, max 1200x1200, quality 80 for better detail while keeping size reasonable (<500KB target)
    Uses in-memory processing for compatibility with cloud storage (e.g., S3) and to avoid temporary files.
    This approach is preferred over file-path based methods as it's more efficient and storage-agnostic.
    Added 'order' field for controlling display sequence, similar to your HotelImage.
    Comparison to your HotelImage optimization:
    - Yours: Saves first, then processes file on disk (assumes local storage), resizes to 1200x1200, quality 80, removes original.
    - This: Processes in-memory before save (better for production, no double save, works with remote storage), similar resize/quality.
    - Verdict: In-memory is best practice (as per Django docs and community examples) for scalability; adopted larger size from yours for car details.
    """
    car = models.ForeignKey(
        Car,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(
        upload_to='cars/%Y/%m/%d/',
        help_text="Car image - will be auto-optimized"
    )
    alt_text = models.CharField(
        max_length=200,
        blank=True,
        help_text="SEO: Description of the image"
    )
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0, help_text="Order for display (lower first)")
    uploaded_at = models.DateTimeField(auto_now_add=True)
   
    class Meta:
        ordering = ['order', '-is_primary', 'uploaded_at']
        verbose_name = "Car Image"
        verbose_name_plural = "Car Images"

    def __str__(self):
        return f"Image for {self.car.title} ({self.order})"

    def save(self, *args, **kwargs):
        """
        SPEED OPTIMIZATION: Compress and resize images on upload in-memory
        - Resize to max 1200x1200 (maintains aspect ratio, larger for better car detail views)
        - Convert to WebP format (better compression)
        - Quality 80 (balance size/quality)
        - No file system ops post-save, compatible with any Django storage backend
        """
        if self.image:
            # Open image with Pillow
            img = Image.open(self.image)
           
            # Convert to RGB if necessary (for WebP compatibility)
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
           
            # Resize maintaining aspect ratio
            max_size = (1200, 1200)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
           
            # Save to BytesIO object
            output = BytesIO()
           
            # Save as WebP with quality optimization
            img.save(output, format='WEBP', quality=80, method=6, optimize=True)
            output.seek(0)
           
            # Replace the image field with optimized version
            self.image = InMemoryUploadedFile(
                output,
                'ImageField',
                f"{self.image.name.split('.')[0]}.webp",
                'image/webp',
                sys.getsizeof(output),
                None
            )
       
        # Auto-generate alt text if not provided
        if not self.alt_text and self.car:
            self.alt_text = f"{self.car.year} {self.car.make} {self.car.model}"
       
        super().save(*args, **kwargs)

class CarInquiry(models.Model):
    """
    Track user inquiries for analytics and follow-up
    """
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='inquiries')
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    contacted = models.BooleanField(default=False)
    converted_to_booking = models.BooleanField(
        default=False,
        help_text="True if this inquiry was converted to a booking"
    )
   
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Car Inquiries"

    def __str__(self):
        return f"Inquiry for {self.car.title} by {self.name}"
    


class CarBooking(models.Model):
    """
    Enhanced booking system with in-app negotiation
    Extends CarInquiry concept but with full journey tracking
    NO USER MODEL NEEDED - Phone/Email based tracking
    """
    # Link to original inquiry (optional - for conversion tracking)
    inquiry = models.OneToOneField(
        'CarInquiry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='booking',
        help_text="Original inquiry that led to this booking"
    )
    
    # Car Information
    car = models.ForeignKey(
        Car,
        on_delete=models.CASCADE,
        related_name='bookings',
        help_text="The car being booked"
    )
    
    # Customer Information (No auth required)
    customer_name = models.CharField(max_length=200)
    customer_phone = models.CharField(max_length=20, db_index=True)
    customer_email = models.EmailField(blank=True)
    
    # Booking Progress
    status = models.CharField(
        max_length=30,
        choices=BOOKING_STATUS_CHOICES,
        default='interest_shown',
        db_index=True
    )
    
    # Stage 2: Inspection
    inspection_date = models.DateTimeField(null=True, blank=True)
    inspection_location = models.CharField(max_length=200, blank=True)
    inspection_notes = models.TextField(blank=True, help_text="Admin notes after inspection")
    
    # Stage 3: Payment
    payment_scheduled_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(
        max_length=100,
        blank=True,
        choices=[
            ('bank_transfer', 'Bank Transfer'),
            ('cash', 'Cash Payment'),
            ('bank_draft', 'Bank Draft'),
            ('pos', 'POS Payment'),
        ]
    )
    
    # Stage 4: Confirmation
    payment_confirmed_date = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=200, blank=True)
    
    # Negotiation Features
    negotiated_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Final negotiated price (if different from listing)"
    )
    
    # Free Gift Tracking
    free_gift_claimed = models.BooleanField(default=False)
    free_gift_claimed_date = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_customer_message = models.DateTimeField(null=True, blank=True)
    last_admin_response = models.DateTimeField(null=True, blank=True)
    
    # Admin Management
    admin_notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    # Notification Preferences
    notify_by_email = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Car Booking"
        verbose_name_plural = "Car Bookings"
        indexes = [
            models.Index(fields=['car', 'status', 'is_active']),
            models.Index(fields=['customer_phone']),
            models.Index(fields=['status', '-updated_at']),
        ]
    
    def __str__(self):
        return f"{self.customer_name} - {self.car.title} ({self.get_status_display()})"
    
    @property
    def has_unread_messages(self):
        """Check if customer has unread admin messages"""
        if not self.last_admin_response:
            return False
        return self.messages.filter(
            is_from_admin=True,
            created_at__gt=self.last_customer_message or timezone.now()
        ).exists()
    
    @property
    def unread_count_for_admin(self):
        """Count unread customer messages for admin"""
        if not self.last_admin_response:
            return self.messages.filter(is_from_admin=False).count()
        return self.messages.filter(
            is_from_admin=False,
            created_at__gt=self.last_admin_response
        ).count()
    
    @property
    def progress_percentage(self):
        """Calculate booking progress"""
        progress_map = {
            'interest_shown': 20,
            'inspection_scheduled': 40,
            'payment_scheduled': 60,
            'payment_confirmed': 80,
            'completed': 100,
            'cancelled': 0,
        }
        return progress_map.get(self.status, 0)
    
    @property
    def final_price(self):
        """Get final price (negotiated or original)"""
        return self.negotiated_price or self.car.price
    
    @property
    def formatted_final_price(self):
        return f"₦{self.final_price:,.0f}"
    
    def clean(self):
        """
        REMOVED: Double booking prevention
        Cars remain available to all customers until actually sold
        """
        pass 
    
    def advance_to_next_stage(self):
        """Move to next stage"""
        transitions = {
            'interest_shown': 'inspection_scheduled',
            'inspection_scheduled': 'payment_scheduled',
            'payment_scheduled': 'payment_confirmed',
            'payment_confirmed': 'completed',
        }
        
        if self.status in transitions:
            self.status = transitions[self.status]
            
            if self.status == 'completed' and not self.free_gift_claimed:
                self.free_gift_claimed = True
                self.free_gift_claimed_date = timezone.now()
            
            self.save()
            
            # Create activity log
            BookingActivity.objects.create(
                booking=self,
                activity_type='status_change',
                title=f'Status updated to {self.get_status_display()}',
                performed_by='Admin',
                is_visible_to_customer=True
            )
            return True
        return False
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class BookingMessage(models.Model):
    """
    In-app messaging between customer and admin
    Replaces WhatsApp - all negotiation happens here
    """
    booking = models.ForeignKey(
        CarBooking,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    
    message = models.TextField()
    
    is_from_admin = models.BooleanField(
        default=False,
        help_text="True if sent by admin, False if sent by customer"
    )
    
    # Optional: Attach price offers during negotiation
    price_offer = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Price offer included in this message"
    )
    
    # Attachments (optional - for inspection photos, documents, etc.)
    attachment = models.FileField(
        upload_to='booking_attachments/%Y/%m/',
        blank=True,
        null=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Read tracking
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name = "Booking Message"
        verbose_name_plural = "Booking Messages"
        indexes = [
            models.Index(fields=['booking', '-created_at']),
            models.Index(fields=['is_from_admin', 'is_read']),
        ]
    
    def __str__(self):
        sender = "Admin" if self.is_from_admin else self.booking.customer_name
        return f"{sender}: {self.message[:50]}..."
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Update last message timestamps on booking
        if self.is_from_admin:
            self.booking.last_admin_response = self.created_at
        else:
            self.booking.last_customer_message = self.created_at
        self.booking.save(update_fields=['last_admin_response', 'last_customer_message', 'updated_at'])


class BookingActivity(models.Model):
    """
    Activity timeline for booking (like order tracking)
    Shows customer what's happening at each stage
    """
    booking = models.ForeignKey(
        CarBooking,
        on_delete=models.CASCADE,
        related_name='activities'
    )
    
    activity_type = models.CharField(
        max_length=50,
        choices=[
            ('status_change', 'Status Changed'),
            ('message', 'Message Sent'),
            ('inspection', 'Inspection Related'),
            ('payment', 'Payment Related'),
            ('note', 'Note Added'),
        ],
        default='note'
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    performed_by = models.CharField(
        max_length=100,
        default='System',
        help_text="Who performed this action (Customer, Admin, System)"
    )
    
    is_visible_to_customer = models.BooleanField(
        default=True,
        help_text="Show this activity to customer in timeline"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Booking Activity"
        verbose_name_plural = "Booking Activities"
    
    def __str__(self):
        return f"{self.booking.customer_name} - {self.title}"