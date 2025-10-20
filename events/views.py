from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Event, EventTariff, Booking
from .utils import normalize_day_of_week, normalize_month, normalize_specific_dates, normalize_time_slots
from django.contrib.auth.models import User
from datetime import datetime, date
import json

@csrf_exempt
@api_view(['POST'])
@transaction.atomic
def create_booking(request):
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        event_id = data.get('event_id')
        tariff_id = data.get('tariff_id')
        booking_date_str = data.get('booking_date')
        booking_time_str = data.get('booking_time')
        participants_count = int(data.get('participants_count', 1))
        comment = data.get('comment', '')
        source = data.get('source', 'website')

        # --- Get main objects ---
        user = get_object_or_404(User, id=user_id) if user_id else None
        event = get_object_or_404(Event, id=event_id)
        
        # If the event has only one tariff, use it
        if not event.has_multiple_tariffs:
            tariff = event.tariffs.first()
            if not tariff:
                return JsonResponse({'error': 'Default tariff not found for this event.'}, status=400)
        else:
            if not tariff_id:
                return JsonResponse({'error': 'Tariff ID is required for events with multiple tariffs.'}, status=400)
            tariff = get_object_or_404(EventTariff, id=tariff_id, event=event)

        # 1. Check Event and Tariff status
        if event.status != 'active' or tariff.status != 'active':
            return JsonResponse({'error': 'Event or tariff is not active.'}, status=400)

        # 2. Validate date and time
        try:
            booking_date = datetime.strptime(booking_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)

        if booking_date < date.today():
            return JsonResponse({'error': 'Booking date cannot be in the past.'}, status=400)

        booking_time = None
        if booking_time_str:
            normalized_time = normalize_time_slots(booking_time_str)
            if not normalized_time:
                 return JsonResponse({'error': 'Invalid time format.'}, status=400)
            booking_time_str = normalized_time[0]
            try:
                booking_time = datetime.strptime(booking_time_str, '%H:%M').time()
                if booking_date == date.today() and booking_time < datetime.now().time():
                    return JsonResponse({'error': 'Booking time cannot be in the past.'}, status=400)
            except (ValueError, TypeError):
                return JsonResponse({'error': 'Invalid time format. Use HH:MM.'}, status=400)

        if tariff.requires_time and not booking_time:
            return JsonResponse({'error': 'This tariff requires a specific time.'}, status=400)
        
        normalized_tariff_slots = normalize_time_slots(tariff.time_slots)
        if tariff.requires_time and normalized_tariff_slots and booking_time_str not in normalized_tariff_slots:
            return JsonResponse({'error': f'Invalid time slot. Available slots are: {", ".join(normalized_tariff_slots)}'}, status=400)

        # 3. Check availability type
        if tariff.availability_type == 'weekly':
            day_of_week = booking_date.strftime('%a').lower()[:3]
            normalized_days = normalize_day_of_week(tariff.days_of_week)
            if normalized_days and 'any' not in normalized_days and day_of_week not in normalized_days:
                return JsonResponse({'error': 'Event is not available on this day of the week.'}, status=400)
            
            month = booking_date.strftime('%b').lower()
            normalized_months = normalize_month(tariff.months)
            if normalized_months and 'any' not in normalized_months and month not in normalized_months:
                 return JsonResponse({'error': 'Event is not available in this month.'}, status=400)

        elif tariff.availability_type == 'specific_dates':
            normalized_dates = normalize_specific_dates(tariff.specific_dates)
            if booking_date_str not in normalized_dates:
                return JsonResponse({'error': 'Event is not available on this date.'}, status=400)

        # 4. Check age (if user has a profile with age)
        if user and hasattr(user, 'profile') and user.profile.birth_date and event.min_age > 0:
            today = date.today()
            age = today.year - user.profile.birth_date.year - ((today.month, today.day) < (user.profile.birth_date.month, user.profile.birth_date.day))
            if age < event.min_age:
                return JsonResponse({'error': f'Minimum age for this event is {event.min_age}.'}, status=400)

        # 5. Check participant count
        if tariff.max_people > 0:
            # Find existing bookings
            existing_bookings = Booking.objects.filter(
                event=event,
                tariff=tariff,
                booking_date=booking_date,
            )
            if booking_time:
                existing_bookings = existing_bookings.filter(booking_time=booking_time)
            
            total_participants = sum(b.participants_count for b in existing_bookings)

            effective_max_people = tariff.max_people
            if tariff.parallel_events and tariff.parallel_events > 1:
                if (participants_count / tariff.parallel_events) > tariff.max_people:
                     return JsonResponse({'error': f'A maximum of {tariff.max_people} participants are allowed per parallel event.'}, status=400)
                effective_max_people *= tariff.parallel_events

            if (total_participants + participants_count) > effective_max_people:
                return JsonResponse({'error': 'The maximum number of participants has been exceeded for this slot.'}, status=400)

        # 6. Create booking
        new_booking = Booking.objects.create(
            user=user,
            event=event,
            tariff=tariff,
            booking_date=booking_date,
            booking_time=booking_time,
            participants_count=participants_count,
            comment=comment,
            source=source,
            status='pending',
            # 'confirmed' is set automatically by the model's save method
        )

        return JsonResponse({'success': True, 'booking_id': new_booking.id, 'confirmed': new_booking.confirmed}, status=201)

    except (Event.DoesNotExist, EventTariff.DoesNotExist, User.DoesNotExist) as e:
        return JsonResponse({'error': str(e)}, status=404)
    except (ValueError, TypeError, KeyError) as e:
        return JsonResponse({'error': f'Invalid data provided: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)

