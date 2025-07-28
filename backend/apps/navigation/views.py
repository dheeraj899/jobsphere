from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.utils import timezone


# Note: No models are currently defined in the navigation app
# This file provides API endpoints for navigation-related functionality

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def main_navigation(request):
    """Get main navigation menu structure"""
    # Define main navigation structure
    navigation = {
        'main_menu': [
            {
                'id': 'jobs',
                'label': 'Jobs',
                'url': '/jobs/',
                'icon': 'briefcase',
                'children': [
                    {'id': 'search-jobs', 'label': 'Search Jobs', 'url': '/jobs/search/'},
                    {'id': 'browse-categories', 'label': 'Browse Categories', 'url': '/jobs/categories/'},
                    {'id': 'saved-jobs', 'label': 'Saved Jobs', 'url': '/jobs/saved/', 'auth_required': True},
                    {'id': 'my-applications', 'label': 'My Applications', 'url': '/jobs/applications/', 'auth_required': True}
                ]
            },
            {
                'id': 'companies',
                'label': 'Companies',
                'url': '/companies/',
                'icon': 'building',
                'children': [
                    {'id': 'browse-companies', 'label': 'Browse Companies', 'url': '/companies/'},
                    {'id': 'company-reviews', 'label': 'Company Reviews', 'url': '/companies/reviews/'}
                ]
            },
            {
                'id': 'profile',
                'label': 'Profile',
                'url': '/profile/',
                'icon': 'user',
                'auth_required': True,
                'children': [
                    {'id': 'my-profile', 'label': 'My Profile', 'url': '/profile/'},
                    {'id': 'resume', 'label': 'Resume', 'url': '/profile/resume/'},
                    {'id': 'settings', 'label': 'Settings', 'url': '/profile/settings/'}
                ]
            },
            {
                'id': 'messages',
                'label': 'Messages',
                'url': '/messages/',
                'icon': 'message-circle',
                'auth_required': True
            }
        ],
        'footer_menu': [
            {
                'id': 'about',
                'label': 'About Us',
                'url': '/about/',
                'icon': 'info'
            },
            {
                'id': 'contact',
                'label': 'Contact',
                'url': '/contact/',
                'icon': 'mail'
            },
            {
                'id': 'privacy',
                'label': 'Privacy Policy',
                'url': '/privacy/',
                'icon': 'shield'
            },
            {
                'id': 'terms',
                'label': 'Terms of Service',
                'url': '/terms/',
                'icon': 'file-text'
            }
        ],
        'user_menu': [
            {
                'id': 'dashboard',
                'label': 'Dashboard',
                'url': '/dashboard/',
                'icon': 'home',
                'auth_required': True
            },
            {
                'id': 'profile',
                'label': 'Profile',
                'url': '/profile/',
                'icon': 'user',
                'auth_required': True
            },
            {
                'id': 'applications',
                'label': 'Applications',
                'url': '/jobs/applications/',
                'icon': 'file-text',
                'auth_required': True
            },
            {
                'id': 'saved-jobs',
                'label': 'Saved Jobs',
                'url': '/jobs/saved/',
                'icon': 'bookmark',
                'auth_required': True
            },
            {
                'id': 'messages',
                'label': 'Messages',
                'url': '/messages/',
                'icon': 'message-circle',
                'auth_required': True,
                'badge': 'unread_count'  # Dynamic badge
            },
            {
                'id': 'settings',
                'label': 'Settings',
                'url': '/profile/settings/',
                'icon': 'settings',
                'auth_required': True
            },
            {
                'id': 'logout',
                'label': 'Logout',
                'url': '/auth/logout/',
                'icon': 'log-out',
                'auth_required': True
            }
        ]
    }
    
    # Filter menu items based on authentication
    if not request.user.is_authenticated:
        # Remove auth-required items for anonymous users
        navigation = _filter_auth_required(navigation, False)
    else:
        # Add dynamic badges for authenticated users
        navigation = _add_dynamic_badges(navigation, request.user)
    
    return Response({
        'navigation': navigation,
        'user_authenticated': request.user.is_authenticated,
        'user_info': {
            'id': request.user.id,
            'username': request.user.username,
            'full_name': f"{request.user.first_name} {request.user.last_name}".strip()
        } if request.user.is_authenticated else None
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def breadcrumbs(request):
    """Generate breadcrumbs based on current path"""
    path = request.query_params.get('path', '/')
    
    # Define breadcrumb mapping
    breadcrumb_map = {
        '/': [{'label': 'Home', 'url': '/'}],
        '/jobs/': [
            {'label': 'Home', 'url': '/'},
            {'label': 'Jobs', 'url': '/jobs/'}
        ],
        '/jobs/search/': [
            {'label': 'Home', 'url': '/'},
            {'label': 'Jobs', 'url': '/jobs/'},
            {'label': 'Search', 'url': '/jobs/search/'}
        ],
        '/profile/': [
            {'label': 'Home', 'url': '/'},
            {'label': 'Profile', 'url': '/profile/'}
        ],
        '/companies/': [
            {'label': 'Home', 'url': '/'},
            {'label': 'Companies', 'url': '/companies/'}
        ]
    }
    
    # Get breadcrumbs for path or generate from path segments
    breadcrumbs = breadcrumb_map.get(path)
    
    if not breadcrumbs:
        # Generate breadcrumbs from path segments
        breadcrumbs = [{'label': 'Home', 'url': '/'}]
        
        segments = [seg for seg in path.split('/') if seg]
        current_path = ''
        
        for segment in segments:
            current_path += f'/{segment}'
            breadcrumbs.append({
                'label': segment.replace('-', ' ').title(),
                'url': current_path + '/'
            })
    
    return Response({
        'breadcrumbs': breadcrumbs,
        'current_path': path
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def quick_actions(request):
    """Get quick action buttons based on user type"""
    actions = []
    
    if request.user.is_authenticated:
        # Authenticated user quick actions
        actions = [
            {
                'id': 'post-job',
                'label': 'Post a Job',
                'url': '/jobs/post/',
                'icon': 'plus-circle',
                'color': 'primary',
                'description': 'Post a new job opening'
            },
            {
                'id': 'search-jobs',
                'label': 'Search Jobs',
                'url': '/jobs/search/',
                'icon': 'search',
                'color': 'secondary',
                'description': 'Find your next opportunity'
            },
            {
                'id': 'update-profile',
                'label': 'Update Profile',
                'url': '/profile/edit/',
                'icon': 'edit',
                'color': 'info',
                'description': 'Keep your profile current'
            },
            {
                'id': 'view-applications',
                'label': 'My Applications',
                'url': '/jobs/applications/',
                'icon': 'file-text',
                'color': 'success',
                'description': 'Track your job applications'
            }
        ]
    else:
        # Anonymous user quick actions
        actions = [
            {
                'id': 'register',
                'label': 'Sign Up',
                'url': '/auth/register/',
                'icon': 'user-plus',
                'color': 'primary',
                'description': 'Create your account'
            },
            {
                'id': 'login',
                'label': 'Login',
                'url': '/auth/login/',
                'icon': 'log-in',
                'color': 'secondary',
                'description': 'Access your account'
            },
            {
                'id': 'browse-jobs',
                'label': 'Browse Jobs',
                'url': '/jobs/',
                'icon': 'briefcase',
                'color': 'info',
                'description': 'Explore job opportunities'
            },
            {
                'id': 'browse-companies',
                'label': 'Browse Companies',
                'url': '/companies/',
                'icon': 'building',
                'color': 'success',
                'description': 'Discover employers'
            }
        ]
    
    return Response({
        'quick_actions': actions,
        'user_authenticated': request.user.is_authenticated
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_navigation_stats(request):
    """Get navigation statistics for authenticated user"""
    user = request.user
    stats = {}
    
    try:
        # Get unread message count
        from apps.messaging.models import Notification
        unread_notifications = Notification.objects.filter(
            user=user,
            is_read=False,
            is_dismissed=False
        ).count()
        stats['unread_notifications'] = unread_notifications
        
        # Get pending applications count
        from apps.jobs.models import JobApplication
        pending_applications = JobApplication.objects.filter(
            applicant=user,
            status='pending'
        ).count()
        stats['pending_applications'] = pending_applications
        
        # Get saved jobs count
        from apps.jobs.models import SavedJob
        saved_jobs_count = SavedJob.objects.filter(user=user).count()
        stats['saved_jobs_count'] = saved_jobs_count
        
    except Exception:
        # If models don't exist or other errors, provide defaults
        stats = {
            'unread_notifications': 0,
            'pending_applications': 0,
            'saved_jobs_count': 0
        }
    
    return Response({
        'stats': stats,
        'user_id': user.id
    })


def _filter_auth_required(navigation, is_authenticated):
    """Filter navigation items based on authentication requirement"""
    filtered_nav = {}
    
    for section_key, section_items in navigation.items():
        filtered_items = []
        
        for item in section_items:
            # Skip items that require authentication if user is not authenticated
            if item.get('auth_required', False) and not is_authenticated:
                continue
            
            # Filter children if present
            if 'children' in item:
                filtered_children = [
                    child for child in item['children']
                    if not child.get('auth_required', False) or is_authenticated
                ]
                item = item.copy()
                item['children'] = filtered_children
            
            filtered_items.append(item)
        
        filtered_nav[section_key] = filtered_items
    
    return filtered_nav


def _add_dynamic_badges(navigation, user):
    """Add dynamic badges to navigation items"""
    try:
        # Get unread notifications count
        from apps.messaging.models import Notification
        unread_count = Notification.objects.filter(
            user=user,
            is_read=False,
            is_dismissed=False
        ).count()
        
        # Add badge to messages in user menu
        for item in navigation.get('user_menu', []):
            if item.get('id') == 'messages' and item.get('badge') == 'unread_count':
                item['badge_count'] = unread_count
                item['badge_visible'] = unread_count > 0
        
    except Exception:
        # If there's an error, just continue without badges
        pass
    
    return navigation


# Future navigation models can be added here:
# - MenuItem model for dynamic menu management
# - UserNavigationPreferences for personalized navigation
# - NavigationAnalytics for tracking navigation usage
# - BreadcrumbHistory for intelligent breadcrumb suggestions

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def sitemap_data(request):
    """Get sitemap data for navigation and SEO"""
    sitemap = {
        'public_pages': [
            {'url': '/', 'title': 'Home', 'priority': 1.0},
            {'url': '/jobs/', 'title': 'Jobs', 'priority': 0.9},
            {'url': '/jobs/search/', 'title': 'Search Jobs', 'priority': 0.8},
            {'url': '/jobs/categories/', 'title': 'Job Categories', 'priority': 0.7},
            {'url': '/companies/', 'title': 'Companies', 'priority': 0.8},
            {'url': '/about/', 'title': 'About Us', 'priority': 0.5},
            {'url': '/contact/', 'title': 'Contact', 'priority': 0.5},
            {'url': '/privacy/', 'title': 'Privacy Policy', 'priority': 0.3},
            {'url': '/terms/', 'title': 'Terms of Service', 'priority': 0.3}
        ],
        'authenticated_pages': [
            {'url': '/dashboard/', 'title': 'Dashboard', 'priority': 0.9},
            {'url': '/profile/', 'title': 'Profile', 'priority': 0.8},
            {'url': '/jobs/applications/', 'title': 'My Applications', 'priority': 0.8},
            {'url': '/jobs/saved/', 'title': 'Saved Jobs', 'priority': 0.7},
            {'url': '/messages/', 'title': 'Messages', 'priority': 0.7},
            {'url': '/profile/settings/', 'title': 'Settings', 'priority': 0.6}
        ]
    }
    
    return Response({
        'sitemap': sitemap,
        'generated_at': timezone.now()
    })
