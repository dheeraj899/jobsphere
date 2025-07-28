from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from .models import UserProfile, Experience, About, Contact
from .serializers import (
    UserProfileSerializer, ExperienceSerializer, AboutSerializer,
    ContactSerializer, UserProfileDetailSerializer, UserSerializer
)


class ProfilePagination(PageNumberPagination):
    """Custom pagination for profile-related views"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class UserProfileView(generics.RetrieveUpdateAPIView):
    """Get, create, or update user profile"""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        """Get or create user profile"""
        profile, created = UserProfile.objects.get_or_create(
            user=self.request.user,
            defaults={
                'bio': '',
                'location': '',
                'is_active': True
            }
        )
        return profile
    
    def retrieve(self, request, *args, **kwargs):
        """Get user profile with additional context"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        # Add completion status
        completion_data = self._calculate_profile_completion(instance)
        
        return Response({
            'profile': serializer.data,
            'completion': completion_data,
            'can_edit': instance.user == request.user
        }, status=status.HTTP_200_OK)
    
    def update(self, request, *args, **kwargs):
        """Update user profile"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Ensure user can only update their own profile
        if instance.user != request.user:
            return Response({
                'error': 'You can only update your own profile'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        
        completion_data = self._calculate_profile_completion(profile)
        
        return Response({
            'message': 'Profile updated successfully',
            'profile': serializer.data,
            'completion': completion_data
        }, status=status.HTTP_200_OK)
    
    def _calculate_profile_completion(self, profile):
        """Calculate profile completion percentage"""
        fields_to_check = [
            'bio', 'location', 'phone', 'website', 'linkedin', 'github'
        ]
        completed_fields = sum(1 for field in fields_to_check if getattr(profile, field))
        
        # Check avatar
        if profile.avatar:
            completed_fields += 1
            fields_to_check.append('avatar')
        
        total_fields = len(fields_to_check)
        percentage = (completed_fields / total_fields) * 100 if total_fields > 0 else 0
        
        return {
            'percentage': round(percentage, 1),
            'completed_fields': completed_fields,
            'total_fields': total_fields,
            'missing_fields': [field for field in fields_to_check if not getattr(profile, field)]
        }


class PublicProfileView(generics.RetrieveAPIView):
    """Public profile view for viewing other users' profiles"""
    serializer_class = UserProfileDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'user__username'
    lookup_url_kwarg = 'username'
    
    def get_queryset(self):
        """Get active, public profiles only"""
        return UserProfile.objects.filter(
            is_active=True,
            user__is_active=True
        ).select_related('user')
    
    def retrieve(self, request, *args, **kwargs):
        """Get public profile with privacy controls"""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            
            # Increment profile view count if different user
            if request.user.is_authenticated and request.user != instance.user:
                # This would typically update a ProfileView model for analytics
                pass
            
            return Response({
                'profile': serializer.data,
                'is_own_profile': request.user.is_authenticated and request.user == instance.user
            }, status=status.HTTP_200_OK)
            
        except UserProfile.DoesNotExist:
            return Response({
                'error': 'Profile not found'
            }, status=status.HTTP_404_NOT_FOUND)


class ExperienceListCreateView(generics.ListCreateAPIView):
    """List and create user experiences"""
    serializer_class = ExperienceSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = ProfilePagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['experience_type', 'is_current']
    ordering = ['-start_date', '-created_at']
    
    def get_queryset(self):
        """Get experiences for authenticated user"""
        if getattr(self, 'swagger_fake_view', False):
            return Experience.objects.none()
        return Experience.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """Create experience for authenticated user"""
        serializer.save(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """Create new experience with validation"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        experience = serializer.save(user=request.user)
        
        return Response({
            'message': 'Experience added successfully',
            'experience': ExperienceSerializer(experience).data
        }, status=status.HTTP_201_CREATED)


class ExperienceDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete specific experience"""
    serializer_class = ExperienceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get experiences for authenticated user only"""
        if getattr(self, 'swagger_fake_view', False):
            return Experience.objects.none()
        return Experience.objects.filter(user=self.request.user)
    
    def update(self, request, *args, **kwargs):
        """Update experience"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        experience = serializer.save()
        
        return Response({
            'message': 'Experience updated successfully',
            'experience': serializer.data
        }, status=status.HTTP_200_OK)
    
    def destroy(self, request, *args, **kwargs):
        """Delete experience"""
        instance = self.get_object()
        instance.delete()
        
        return Response({
            'message': 'Experience deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)


class AboutView(generics.RetrieveUpdateAPIView):
    """Get, create, or update user's about information"""
    serializer_class = AboutSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        """Get or create about information"""
        about, created = About.objects.get_or_create(
            user=self.request.user,
            defaults={
                'summary': '',
                'skills': '',
                'interests': '',
                'languages': '',
                'years_of_experience': 0
            }
        )
        return about
    
    def retrieve(self, request, *args, **kwargs):
        """Get about information"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        return Response({
            'about': serializer.data,
            'completion_percentage': self._calculate_about_completion(instance)
        }, status=status.HTTP_200_OK)
    
    def update(self, request, *args, **kwargs):
        """Update about information"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        about = serializer.save()
        
        return Response({
            'message': 'About information updated successfully',
            'about': serializer.data,
            'completion_percentage': self._calculate_about_completion(about)
        }, status=status.HTTP_200_OK)
    
    def _calculate_about_completion(self, about):
        """Calculate about section completion percentage"""
        fields = ['summary', 'skills', 'interests', 'languages']
        completed = sum(1 for field in fields if getattr(about, field))
        
        # Add years of experience if > 0
        if about.years_of_experience > 0:
            completed += 1
            fields.append('years_of_experience')
        
        percentage = (completed / len(fields)) * 100 if fields else 0
        return round(percentage, 1)


class ContactView(generics.RetrieveUpdateAPIView):
    """Get, create, or update user's contact information"""
    serializer_class = ContactSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        """Get or create contact information"""
        contact, created = Contact.objects.get_or_create(
            user=self.request.user,
            defaults={
                'primary_email': self.request.user.email,
                'secondary_email': '',
                'primary_phone': '',
                'secondary_phone': '',
                'address': '',
                'city': '',
                'state': '',
                'country': '',
                'postal_code': '',
                'additional_contacts': {}
            }
        )
        return contact
    
    def retrieve(self, request, *args, **kwargs):
        """Get contact information with privacy controls"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, context={'request': request})
        
        return Response({
            'contact': serializer.data,
            'privacy_level': self._get_privacy_level(instance)
        }, status=status.HTTP_200_OK)
    
    def update(self, request, *args, **kwargs):
        """Update contact information"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        serializer = self.get_serializer(
            instance, 
            data=request.data, 
            partial=partial,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        contact = serializer.save()
        
        return Response({
            'message': 'Contact information updated successfully',
            'contact': serializer.data,
            'privacy_level': self._get_privacy_level(contact)
        }, status=status.HTTP_200_OK)
    
    def _get_privacy_level(self, contact):
        """Determine privacy level based on filled fields"""
        public_fields = ['primary_email', 'city', 'state', 'country']
        private_fields = ['primary_phone', 'secondary_phone', 'address', 'postal_code']
        
        public_filled = sum(1 for field in public_fields if getattr(contact, field))
        private_filled = sum(1 for field in private_fields if getattr(contact, field))
        
        if private_filled > 0:
            return 'detailed'
        elif public_filled >= 3:
            return 'public'
        else:
            return 'minimal'


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def profile_stats(request):
    """Get comprehensive profile statistics"""
    user = request.user
    
    try:
        profile = user.userprofile
        experiences_count = user.experiences.count()
        
        # Get about and contact info
        about_exists = hasattr(user, 'about') and user.about.summary
        contact_exists = hasattr(user, 'contact')
        
        # Calculate overall completion
        sections = {
            'basic_profile': bool(profile.bio and profile.location),
            'avatar': bool(profile.avatar),
            'contact_info': contact_exists,
            'about_section': about_exists,
            'experience': experiences_count > 0,
            'social_links': bool(profile.linkedin or profile.github)
        }
        
        completed_sections = sum(sections.values())
        total_sections = len(sections)
        overall_completion = (completed_sections / total_sections) * 100
        
        return Response({
            'stats': {
                'overall_completion': round(overall_completion, 1),
                'experiences_count': experiences_count,
                'sections_completed': completed_sections,
                'total_sections': total_sections,
                'profile_views': getattr(profile, 'view_count', 0),
                'last_updated': profile.updated_at,
            },
            'sections': sections
        }, status=status.HTTP_200_OK)
        
    except UserProfile.DoesNotExist:
        return Response({
            'error': 'Profile not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def upload_avatar(request):
    """Upload user avatar"""
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    
    if 'avatar' not in request.FILES:
        return Response({
            'error': 'No avatar file provided'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    avatar = request.FILES['avatar']
    
    # Validate file size (5MB limit)
    if avatar.size > 5 * 1024 * 1024:
        return Response({
            'error': 'Avatar file too large. Maximum size is 5MB.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Validate file type
    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    if avatar.content_type not in allowed_types:
        return Response({
            'error': 'Invalid file type. Please upload a JPEG, PNG, GIF, or WebP image.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Update avatar
    profile.avatar = avatar
    profile.save(update_fields=['avatar', 'updated_at'])
    
    return Response({
        'message': 'Avatar uploaded successfully',
        'avatar_url': profile.avatar.url if profile.avatar else None
    }, status=status.HTTP_200_OK) 