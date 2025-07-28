from django.shortcuts import render
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from .models import Dashboard
from .serializers import DashboardSerializer, DashboardUpdateSerializer


class DashboardView(generics.RetrieveUpdateAPIView):
    """Get and update user dashboard"""
    serializer_class = DashboardSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        """Get or create dashboard for user"""
        dashboard, created = Dashboard.objects.get_or_create(
            user=self.request.user,
            defaults={
                'total_applications': 0,
                'active_applications': 0,
                'jobs_posted': 0,
                'profile_views': 0,
                'dashboard_layout': {},
                'notification_preferences': {
                    'email_notifications': True,
                    'push_notifications': True,
                    'job_alerts': True,
                    'application_updates': True
                }
            }
        )
        return dashboard
    
    def retrieve(self, request, *args, **kwargs):
        """Get dashboard with real-time statistics"""
        dashboard = self.get_object()
        
        # Update statistics from related models
        self._update_dashboard_stats(dashboard)
        
        serializer = self.get_serializer(dashboard)
        
        # Add recent activity
        recent_activity = self._get_recent_activity(request.user)
        
        return Response({
            'dashboard': serializer.data,
            'recent_activity': recent_activity,
            'last_updated': dashboard.last_updated
        })
    
    def get_serializer_class(self):
        """Use different serializer for updates"""
        if self.request.method in ['PUT', 'PATCH']:
            return DashboardUpdateSerializer
        return DashboardSerializer
    
    def update(self, request, *args, **kwargs):
        """Update dashboard preferences"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        dashboard = serializer.save()
        
        # Return full dashboard data
        full_serializer = DashboardSerializer(dashboard)
        
        return Response({
            'message': 'Dashboard updated successfully',
            'dashboard': full_serializer.data
        })
    
    def _update_dashboard_stats(self, dashboard):
        """Update dashboard statistics from related models"""
        user = dashboard.user
        
        try:
            # Update job application stats
            from apps.jobs.models import JobApplication
            applications = JobApplication.objects.filter(applicant=user)
            
            application_stats = applications.aggregate(
                total=Count('id'),
                active=Count('id', filter=models.Q(status__in=['pending', 'reviewed', 'interview'])),
                pending=Count('id', filter=models.Q(status='pending')),
                reviewed=Count('id', filter=models.Q(status='reviewed')),
                interview=Count('id', filter=models.Q(status='interview')),
                accepted=Count('id', filter=models.Q(status='accepted')),
                rejected=Count('id', filter=models.Q(status='rejected'))
            )
            
            # Update job posting stats
            from apps.jobs.models import Job
            jobs = Job.objects.filter(posted_by=user)
            
            job_stats = jobs.aggregate(
                total=Count('id'),
                active=Count('id', filter=models.Q(status='published')),
                applications_received=Count('applications')
            )
            
            # Update fields
            fields_to_update = []
            
            if dashboard.total_applications != application_stats['total']:
                dashboard.total_applications = application_stats['total'] or 0
                fields_to_update.append('total_applications')
            
            if dashboard.active_applications != application_stats['active']:
                dashboard.active_applications = application_stats['active'] or 0
                fields_to_update.append('active_applications')
            
            if dashboard.pending_applications != application_stats['pending']:
                dashboard.pending_applications = application_stats['pending'] or 0
                fields_to_update.append('pending_applications')
            
            if dashboard.reviewed_applications != application_stats['reviewed']:
                dashboard.reviewed_applications = application_stats['reviewed'] or 0
                fields_to_update.append('reviewed_applications')
            
            if dashboard.interview_applications != application_stats['interview']:
                dashboard.interview_applications = application_stats['interview'] or 0
                fields_to_update.append('interview_applications')
            
            if dashboard.accepted_applications != application_stats['accepted']:
                dashboard.accepted_applications = application_stats['accepted'] or 0
                fields_to_update.append('accepted_applications')
            
            if dashboard.rejected_applications != application_stats['rejected']:
                dashboard.rejected_applications = application_stats['rejected'] or 0
                fields_to_update.append('rejected_applications')
            
            if dashboard.jobs_posted != job_stats['total']:
                dashboard.jobs_posted = job_stats['total'] or 0
                fields_to_update.append('jobs_posted')
            
            if dashboard.active_job_posts != job_stats['active']:
                dashboard.active_job_posts = job_stats['active'] or 0
                fields_to_update.append('active_job_posts')
            
            if dashboard.total_job_applications_received != job_stats['applications_received']:
                dashboard.total_job_applications_received = job_stats['applications_received'] or 0
                fields_to_update.append('total_job_applications_received')
            
            # Update profile views if available
            try:
                profile = user.userprofile
                if hasattr(profile, 'view_count') and dashboard.profile_views != profile.view_count:
                    dashboard.profile_views = profile.view_count
                    fields_to_update.append('profile_views')
            except:
                pass
            
            # Update if there are changes
            if fields_to_update:
                fields_to_update.extend(['stats_updated_at', 'last_updated'])
                dashboard.stats_updated_at = timezone.now()
                dashboard.save(update_fields=fields_to_update)
                
        except Exception as e:
            # Log error but don't fail the request
            pass
    
    def _get_recent_activity(self, user):
        """Get recent user activity"""
        activities = []
        
        try:
            # Recent job applications
            from apps.jobs.models import JobApplication
            recent_applications = JobApplication.objects.filter(
                applicant=user
            ).order_by('-applied_at')[:5]
            
            for app in recent_applications:
                activities.append({
                    'type': 'job_application',
                    'title': f'Applied to {app.job.title}',
                    'description': f'at {app.job.company}',
                    'timestamp': app.applied_at,
                    'status': app.status,
                    'link': f'/jobs/{app.job.id}/'
                })
            
            # Recent job posts
            from apps.jobs.models import Job
            recent_jobs = Job.objects.filter(
                posted_by=user
            ).order_by('-created_at')[:3]
            
            for job in recent_jobs:
                activities.append({
                    'type': 'job_post',
                    'title': f'Posted job: {job.title}',
                    'description': f'{job.applications.count()} applications received',
                    'timestamp': job.created_at,
                    'status': job.status,
                    'link': f'/jobs/{job.id}/'
                })
            
            # Sort by timestamp
            activities.sort(key=lambda x: x['timestamp'], reverse=True)
            
        except Exception as e:
            pass
        
        return activities[:10]  # Return top 10


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_summary(request):
    """Get dashboard summary statistics"""
    user = request.user
    
    try:
        dashboard = Dashboard.objects.get(user=user)
    except Dashboard.DoesNotExist:
        # Create dashboard if doesn't exist
        dashboard = Dashboard.objects.create(user=user)
    
    # Calculate derived metrics
    total_apps = dashboard.total_applications
    success_rate = 0
    if total_apps > 0:
        success_rate = (dashboard.accepted_applications / total_apps) * 100
    
    response_rate = 0
    if total_apps > 0:
        responded = dashboard.reviewed_applications + dashboard.interview_applications + dashboard.accepted_applications + dashboard.rejected_applications
        response_rate = (responded / total_apps) * 100
    
    summary = {
        'job_seeker_stats': {
            'total_applications': total_apps,
            'active_applications': dashboard.active_applications,
            'success_rate': round(success_rate, 1),
            'response_rate': round(response_rate, 1),
            'pending_applications': dashboard.pending_applications,
            'interviews_scheduled': dashboard.interview_applications
        },
        'employer_stats': {
            'jobs_posted': dashboard.jobs_posted,
            'active_job_posts': dashboard.active_job_posts,
            'applications_received': dashboard.total_job_applications_received,
            'positions_filled': dashboard.jobs_filled
        },
        'profile_stats': {
            'profile_views': dashboard.profile_views,
            'last_updated': dashboard.last_updated
        }
    }
    
    return Response(summary)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def activity_timeline(request):
    """Get user activity timeline"""
    user = request.user
    days = int(request.query_params.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    timeline = []
    
    try:
        # Job applications over time
        from apps.jobs.models import JobApplication
        applications = JobApplication.objects.filter(
            applicant=user,
            applied_at__gte=start_date
        ).values(
            'applied_at__date'
        ).annotate(
            count=Count('id')
        ).order_by('applied_at__date')
        
        app_data = {item['applied_at__date']: item['count'] for item in applications}
        
        # Job posts over time
        from apps.jobs.models import Job
        jobs = Job.objects.filter(
            posted_by=user,
            created_at__gte=start_date
        ).values(
            'created_at__date'
        ).annotate(
            count=Count('id')
        ).order_by('created_at__date')
        
        job_data = {item['created_at__date']: item['count'] for item in jobs}
        
        # Generate timeline
        current_date = start_date.date()
        end_date = timezone.now().date()
        
        while current_date <= end_date:
            timeline.append({
                'date': current_date,
                'applications': app_data.get(current_date, 0),
                'job_posts': job_data.get(current_date, 0)
            })
            current_date += timedelta(days=1)
            
    except Exception as e:
        pass
    
    return Response({
        'timeline': timeline,
        'period_days': days,
        'start_date': start_date.date(),
        'end_date': timezone.now().date()
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def reset_dashboard(request):
    """Reset dashboard to default settings"""
    try:
        dashboard = Dashboard.objects.get(user=request.user)
        
        # Reset layout and preferences
        dashboard.dashboard_layout = {}
        dashboard.notification_preferences = {
            'email_notifications': True,
            'push_notifications': True,
            'job_alerts': True,
            'application_updates': True,
            'message_notifications': True,
            'system_notifications': True
        }
        dashboard.save(update_fields=['dashboard_layout', 'notification_preferences', 'last_updated'])
        
        return Response({
            'message': 'Dashboard reset to default settings successfully'
        })
        
    except Dashboard.DoesNotExist:
        return Response({
            'error': 'Dashboard not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def performance_metrics(request):
    """Get user performance metrics"""
    user = request.user
    
    try:
        dashboard = Dashboard.objects.get(user=user)
        
        # Calculate performance metrics
        metrics = {
            'application_success_rate': 0,
            'response_rate': 0,
            'average_time_to_response': 0,
            'interview_conversion_rate': 0,
            'job_posting_effectiveness': 0
        }
        
        # Application metrics
        if dashboard.total_applications > 0:
            metrics['application_success_rate'] = (dashboard.accepted_applications / dashboard.total_applications) * 100
            
            responded = (dashboard.reviewed_applications + dashboard.interview_applications + 
                        dashboard.accepted_applications + dashboard.rejected_applications)
            metrics['response_rate'] = (responded / dashboard.total_applications) * 100
            
            if dashboard.reviewed_applications > 0:
                metrics['interview_conversion_rate'] = (dashboard.interview_applications / dashboard.reviewed_applications) * 100
        
        # Employer metrics
        if dashboard.jobs_posted > 0:
            metrics['job_posting_effectiveness'] = (dashboard.total_job_applications_received / dashboard.jobs_posted)
        
        # Round all metrics
        for key, value in metrics.items():
            metrics[key] = round(value, 2) if isinstance(value, float) else value
        
        return Response({
            'metrics': metrics,
            'calculated_at': timezone.now()
        })
        
    except Dashboard.DoesNotExist:
        return Response({
            'metrics': {
                'application_success_rate': 0,
                'response_rate': 0,
                'average_time_to_response': 0,
                'interview_conversion_rate': 0,
                'job_posting_effectiveness': 0
            }
        })
