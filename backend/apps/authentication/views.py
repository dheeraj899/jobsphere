from django.shortcuts import render
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.conf import settings
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, PasswordChangeSerializer,
    PasswordResetSerializer, PasswordResetConfirmSerializer, UserProfileUpdateSerializer
)
from django.utils import timezone
from apps.authentication.tasks import send_password_reset_email_task


class LoginRateThrottle(AnonRateThrottle):
    """Custom throttle for login attempts"""
    scope = 'login'
    rate = '5/min'


class RegistrationRateThrottle(AnonRateThrottle):
    """Custom throttle for registration attempts"""
    scope = 'register'
    rate = '3/min'


class UserRegistrationView(generics.CreateAPIView):
    """User registration endpoint"""
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [RegistrationRateThrottle]
    
    def create(self, request, *args, **kwargs):
        """Create new user account"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.save()
        
        # Generate JWT tokens for the new user
        refresh = RefreshToken.for_user(user)
        
        # Send welcome email (optional)
        try:
            send_mail(
                'Welcome to JobSphere!',
                f'Welcome {user.first_name}! Your account has been created successfully.',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True,
            )
        except Exception:
            pass  # Email sending failure shouldn't block registration
        
        return Response({
            'message': 'User registered successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            },
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        }, status=status.HTTP_201_CREATED)


class UserLoginView(TokenObtainPairView):
    """Enhanced login view with custom response"""
    serializer_class = UserLoginSerializer
    throttle_classes = [LoginRateThrottle]
    
    def post(self, request, *args, **kwargs):
        """Authenticate user and return tokens"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        
        # Update last login
        from django.contrib.auth import update_session_auth_hash
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        
        return Response({
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_staff': user.is_staff,
                'is_active': user.is_active,
            },
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        }, status=status.HTTP_200_OK)


class UserLogoutView(generics.GenericAPIView):
    """User logout endpoint - blacklist refresh token"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Logout user by blacklisting refresh token"""
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            return Response({
                'message': 'Logout successful'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': 'Invalid token'
            }, status=status.HTTP_400_BAD_REQUEST)


class PasswordChangeView(generics.UpdateAPIView):
    """Change password for authenticated users"""
    serializer_class = PasswordChangeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        """Update user password"""
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        user = serializer.save()
        
        return Response({
            'message': 'Password changed successfully'
        }, status=status.HTTP_200_OK)


class PasswordResetView(generics.GenericAPIView):
    """Request password reset via email"""
    serializer_class = PasswordResetSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]
    
    def post(self, request):
        """Send password reset email"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        try:
            user = User.objects.get(email=email)
            
            # Generate reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Send reset email
            reset_url = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/"
            # Send password reset email asynchronously
            send_password_reset_email_task.delay(email, reset_url)
            
            return Response({
                'message': 'Password reset email sent successfully'
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            # Don't reveal if email exists
            return Response({
                'message': 'Password reset email sent successfully'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': 'Failed to send reset email'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PasswordResetConfirmView(generics.GenericAPIView):
    """Confirm password reset with token"""
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Reset password with valid token"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            uid = force_str(urlsafe_base64_decode(serializer.validated_data['uid']))
            user = User.objects.get(pk=uid)
            token = serializer.validated_data['token']
            
            if default_token_generator.check_token(user, token):
                user.set_password(serializer.validated_data['new_password'])
                user.save()
                
                return Response({
                    'message': 'Password reset successful'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'Invalid or expired token'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({
                'error': 'Invalid token'
            }, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """Get and update user profile"""
    serializer_class = UserProfileUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def retrieve(self, request, *args, **kwargs):
        """Get user profile"""
        user = self.get_object()
        serializer = self.get_serializer(user)
        
        return Response({
            'user': serializer.data,
            'profile_completion': self._calculate_profile_completion(user)
        }, status=status.HTTP_200_OK)
    
    def update(self, request, *args, **kwargs):
        """Update user profile"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.save()
        
        return Response({
            'message': 'Profile updated successfully',
            'user': serializer.data,
            'profile_completion': self._calculate_profile_completion(user)
        }, status=status.HTTP_200_OK)
    
    def _calculate_profile_completion(self, user):
        """Calculate profile completion percentage"""
        fields_to_check = ['first_name', 'last_name', 'email']
        completed_fields = sum(1 for field in fields_to_check if getattr(user, field))
        
        # Check if user has profile extensions
        profile_extensions = 0
        try:
            if hasattr(user, 'userprofile'):
                profile_extensions += 1
            if hasattr(user, 'about'):
                profile_extensions += 1
            if hasattr(user, 'contact'):
                profile_extensions += 1
        except:
            pass
        
        total_possible = len(fields_to_check) + 3  # 3 profile extensions
        completion_percentage = ((completed_fields + profile_extensions) / total_possible) * 100
        
        return {
            'percentage': round(completion_percentage, 1),
            'completed_fields': completed_fields,
            'total_fields': len(fields_to_check),
            'has_extended_profile': profile_extensions > 0
        }


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_dashboard_data(request):
    """Get user dashboard data"""
    user = request.user
    
    # Get basic stats
    stats = {
        'account_created': user.date_joined,
        'last_login': user.last_login,
        'is_active': user.is_active,
        'email_verified': user.is_active,  # Assuming is_active means email verified
    }
    
    # Add related data if available
    try:
        if hasattr(user, 'dashboard'):
            dashboard = user.dashboard
            stats.update({
                'total_applications': dashboard.total_applications,
                'active_applications': dashboard.active_applications,
                'jobs_posted': dashboard.jobs_posted,
                'profile_views': dashboard.profile_views,
            })
    except:
        pass
    
    return Response({
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
        },
        'stats': stats
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def change_email(request):
    """Change user email with verification"""
    new_email = request.data.get('email')
    if not new_email:
        return Response({
            'error': 'Email is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if email already exists
    if User.objects.filter(email=new_email).exclude(pk=request.user.pk).exists():
        return Response({
            'error': 'Email already in use'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Update email
    request.user.email = new_email
    request.user.save(update_fields=['email'])
    
    return Response({
        'message': 'Email updated successfully'
    }, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_account(request):
    """Delete user account"""
    password = request.data.get('password')
    if not password:
        return Response({
            'error': 'Password required for account deletion'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Verify password
    if not request.user.check_password(password):
        return Response({
            'error': 'Invalid password'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Soft delete - deactivate account
    request.user.is_active = False
    request.user.save(update_fields=['is_active'])
    
    return Response({
        'message': 'Account deactivated successfully'
    }, status=status.HTTP_200_OK)
