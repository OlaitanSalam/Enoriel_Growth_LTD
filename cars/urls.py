from django.urls import path
from . import views

"""
URL Configuration for Enoriel Cars Platform
Clean, SEO-friendly URL structure
"""

urlpatterns = [
    # Homepage
    path('', views.HomeView.as_view(), name='home'),

    # about
     path('about/', views.about_view, name='about'),
     path('contact/', views.contact_view, name='contact'),
    # Car Listings
    path('', views.HomeView.as_view(), name='home'),
    path('cars/', views.CarListView.as_view(), name='car_list'),
    path('cars/<slug:slug>/', views.CarDetailView.as_view(), name='car_detail'),
    
    # Category Pages
    path('category/<slug:slug>/', views.CategoryListView.as_view(), name='category_list'),
    # Section Pages (NEW)
    path('section/<str:section>/', views.SectionListView.as_view(), name='section_list'),
    
    # Admin/CRUD Operations (protected by LoginRequiredMixin)
    path('admin/cars/new/', views.CarCreateView.as_view(), name='car_create'),
    path('admin/cars/<slug:slug>/edit/', views.CarUpdateView.as_view(), name='car_update'),
    path('admin/cars/<slug:slug>/delete/', views.CarDeleteView.as_view(), name='car_delete'),
     path('api/category-cars/', views.get_category_cars, name='get_category_cars'),


     path('booking/create/', 
         views.create_booking_from_inquiry, 
         name='create_booking_from_inquiry'),
    
    
    
    # Main booking detail page (with chat)
    path('booking/<int:booking_id>/', 
         views.booking_detail, 
         name='booking_detail'),
    
    # Schedule inspection
    path('booking/<int:booking_id>/schedule-inspection/', 
         views.schedule_inspection, 
         name='schedule_inspection'),
    
    # Schedule payment
    path('booking/<int:booking_id>/schedule-payment/', 
         views.schedule_payment, 
         name='schedule_payment'),
    
    # API for real-time updates
    path('api/booking/<int:booking_id>/updates/', 
         views.booking_updates_api, 
         name='booking_updates_api'),
    
    # Customer dashboard - view all bookings
    path('my-bookings/', 
         views.my_bookings, 
         name='my_bookings'),
]



"""
Example URLs generated:
- / (homepage)
- /cars/ (all listings)
- /cars/2020-toyota-corolla/ (detail page)
- /category/suv/ (category page)
- /admin/cars/new/ (create new listing)
- /admin/cars/2020-toyota-corolla/edit/ (edit listing)
- /admin/cars/2020-toyota-corolla/delete/ (delete listing)
"""