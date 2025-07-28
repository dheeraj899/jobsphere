from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.db.models import Q, Count, Avg, F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import Job, JobApplication, JobView, SavedJob
from .serializers import (
    JobSerializer, JobListSerializer, JobCreateSerializer,
    JobApplicationSerializer, JobApplicationCreateSerializer,
    JobViewSerializer, SavedJobSerializer
)


class JobPagination(PageNumberPagination):
    """Custom pagination for job listings"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Custom permission to only allow owners to edit their jobs"""
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only to the owner
        return obj.posted_by == request.user


class JobListCreateView(generics.ListCreateAPIView):
    """List and create jobs with advanced filtering and search"""
    pagination_class = JobPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'job_type', 'experience_level', 'category', 'location',
        'is_remote', 'remote_type', 'status'
    ]
    search_fields = ['title', 'company', 'description', 'skills_required']
    ordering_fields = ['created_at', 'published_at', 'application_deadline', 'salary_min']
    ordering = ['-published_at', '-created_at']
    
    def get_serializer_class(self):
        """Use different serializers for list and create"""
        if self.request.method == 'POST':
            return JobCreateSerializer
        return JobListSerializer
    
    def get_permissions(self):
        """Different permissions for list vs create"""
        if self.request.method == 'POST':
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Get active jobs with optimized queries"""
        queryset = Job.objects.filter(
            status='published',
            application_deadline__gt=timezone.now()
        ).select_related('location', 'posted_by').annotate(
            application_count=Count('applications'),
            view_count=Count('views')
        )
        
        # Full-text search if query provided
        search_query = self.request.query_params.get('search')
        if search_query:
            search_vector = SearchVector('title', 'company', 'description', 'skills_required')
            search_query_obj = SearchQuery(search_query)
            queryset = queryset.annotate(
                search=search_vector,
                rank=SearchRank(search_vector, search_query_obj)
            ).filter(search=search_query_obj).order_by('-rank', '-published_at')
        
        # Salary range filtering
        min_salary = self.request.query_params.get('min_salary')
        max_salary = self.request.query_params.get('max_salary')
        
        if min_salary:
            queryset = queryset.filter(salary_min__gte=min_salary)
        if max_salary:
            queryset = queryset.filter(salary_max__lte=max_salary)
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """Enhanced list with metadata"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Get aggregated stats
        stats = queryset.aggregate(
            total_jobs=Count('id'),
            avg_salary_min=Avg('salary_min'),
            avg_salary_max=Avg('salary_max'),
            remote_jobs=Count('id', filter=Q(is_remote=True))
        )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data['stats'] = stats
            return response
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'results': serializer.data,
            'stats': stats
        })
    
    def perform_create(self, serializer):
        """Create job with posted_by set to current user"""
        serializer.save(posted_by=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """Create job with enhanced response"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        job = serializer.save(posted_by=request.user)
        
        # Return full job data
        response_serializer = JobSerializer(job)
        
        return Response({
            'message': 'Job posted successfully',
            'job': response_serializer.data
        }, status=status.HTTP_201_CREATED)


class JobDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete specific job"""
    serializer_class = JobSerializer
    permission_classes = [IsOwnerOrReadOnly]
    
    def get_queryset(self):
        """Get jobs with related data"""
        if getattr(self, 'swagger_fake_view', False):
            return Job.objects.none()
        return Job.objects.select_related('location', 'posted_by')
    
    def retrieve(self, request, *args, **kwargs):
        """Get job with view tracking"""
        instance = self.get_object()
        
        # Track job view
        if request.user.is_authenticated and request.user != instance.posted_by:
            JobView.objects.get_or_create(
                job=instance,
                user=request.user,
                defaults={
                    'ip_address': self._get_client_ip(request),
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'referrer': request.META.get('HTTP_REFERER', ''),
                    'source': 'web'
                }
            )
        
        serializer = self.get_serializer(instance)
        
        # Add application status if user is authenticated
        user_application = None
        if request.user.is_authenticated:
            try:
                user_application = JobApplication.objects.get(
                    job=instance, 
                    applicant=request.user
                )
            except JobApplication.DoesNotExist:
                pass
        
        # Check if job is saved by user
        is_saved = False
        if request.user.is_authenticated:
            is_saved = SavedJob.objects.filter(
                job=instance,
                user=request.user
            ).exists()
        
        return Response({
            'job': serializer.data,
            'user_application': JobApplicationSerializer(user_application).data if user_application else None,
            'is_saved': is_saved,
            'can_edit': instance.posted_by == request.user,
            'can_apply': (
                request.user.is_authenticated and 
                request.user != instance.posted_by and 
                not user_application and
                instance.status == 'published' and
                instance.application_deadline > timezone.now()
            )
        })
    
    def update(self, request, *args, **kwargs):
        """Update job"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        job = serializer.save()
        
        return Response({
            'message': 'Job updated successfully',
            'job': serializer.data
        })
    
    def destroy(self, request, *args, **kwargs):
        """Delete job"""
        instance = self.get_object()
        instance.delete()
        
        return Response({
            'message': 'Job deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class JobApplicationListCreateView(generics.ListCreateAPIView):
    """List and create job applications"""
    serializer_class = JobApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = JobPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'job__job_type', 'job__category']
    ordering_fields = ['applied_at', 'last_contacted']
    ordering = ['-applied_at']
    
    def get_serializer_class(self):
        """Use different serializers for list and create"""
        if self.request.method == 'POST':
            return JobApplicationCreateSerializer
        return JobApplicationSerializer
    
    def get_queryset(self):
        """Get applications for authenticated user"""
        return JobApplication.objects.filter(
            applicant=self.request.user
        ).select_related('job', 'job__location', 'job__posted_by')
    
    def create(self, request, *args, **kwargs):
        """Create job application with validation"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        job_id = request.data.get('job')
        job = get_object_or_404(Job, id=job_id)
        
        # Validate application eligibility
        if job.posted_by == request.user:
            return Response({
                'error': 'You cannot apply to your own job'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if job.status != 'published':
            return Response({
                'error': 'This job is not accepting applications'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if job.application_deadline <= timezone.now():
            return Response({
                'error': 'Application deadline has passed'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check for existing application
        if JobApplication.objects.filter(job=job, applicant=request.user).exists():
            return Response({
                'error': 'You have already applied to this job'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        application = serializer.save(applicant=request.user, job=job)
        
        return Response({
            'message': 'Application submitted successfully',
            'application': JobApplicationSerializer(application).data
        }, status=status.HTTP_201_CREATED)


class JobApplicationDetailView(generics.RetrieveUpdateAPIView):
    """Retrieve and update job application"""
    serializer_class = JobApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get applications for authenticated user"""
        return JobApplication.objects.filter(
            applicant=self.request.user
        ).select_related('job', 'job__posted_by')
    
    def update(self, request, *args, **kwargs):
        """Update application (limited fields)"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Only allow updating certain fields
        allowed_fields = ['cover_letter', 'portfolio_url']
        data = {k: v for k, v in request.data.items() if k in allowed_fields}
        
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        application = serializer.save()
        
        return Response({
            'message': 'Application updated successfully',
            'application': serializer.data
        })


class SavedJobListCreateView(generics.ListCreateAPIView):
    """List and create saved jobs"""
    serializer_class = SavedJobSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = JobPagination
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get saved jobs for authenticated user"""
        return SavedJob.objects.filter(
            user=self.request.user
        ).select_related('job', 'job__location', 'job__posted_by')
    
    def create(self, request, *args, **kwargs):
        """Save a job"""
        job_id = request.data.get('job')
        if not job_id:
            return Response({
                'error': 'Job ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        job = get_object_or_404(Job, id=job_id)
        
        # Check if already saved
        saved_job, created = SavedJob.objects.get_or_create(
            user=request.user,
            job=job,
            defaults={'notes': request.data.get('notes', '')}
        )
        
        if not created:
            return Response({
                'message': 'Job already saved'
            }, status=status.HTTP_200_OK)
        
        return Response({
            'message': 'Job saved successfully',
            'saved_job': SavedJobSerializer(saved_job).data
        }, status=status.HTTP_201_CREATED)


class SavedJobDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete saved job"""
    serializer_class = SavedJobSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get saved jobs for authenticated user"""
        return SavedJob.objects.filter(user=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        """Unsave a job"""
        instance = self.get_object()
        instance.delete()
        
        return Response({
            'message': 'Job removed from saved list'
        }, status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_jobs(request):
    """Get jobs posted by authenticated user"""
    jobs = Job.objects.filter(
        posted_by=request.user
    ).annotate(
        application_count=Count('applications'),
        view_count=Count('views')
    ).order_by('-created_at')
    
    serializer = JobListSerializer(jobs, many=True)
    
    # Get statistics
    stats = jobs.aggregate(
        total_jobs=Count('id'),
        published_jobs=Count('id', filter=Q(status='published')),
        draft_jobs=Count('id', filter=Q(status='draft')),
        total_applications=Count('applications'),
        total_views=Count('views')
    )
    
    return Response({
        'jobs': serializer.data,
        'stats': stats
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def application_stats(request):
    """Get application statistics for user"""
    applications = JobApplication.objects.filter(applicant=request.user)
    
    stats = applications.aggregate(
        total_applications=Count('id'),
        pending=Count('id', filter=Q(status='pending')),
        reviewed=Count('id', filter=Q(status='reviewed')),
        interview=Count('id', filter=Q(status='interview')),
        accepted=Count('id', filter=Q(status='accepted')),
        rejected=Count('id', filter=Q(status='rejected'))
    )
    
    # Recent applications
    recent_applications = applications.order_by('-applied_at')[:5]
    recent_serializer = JobApplicationSerializer(recent_applications, many=True)
    
    return Response({
        'stats': stats,
        'recent_applications': recent_serializer.data
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def withdraw_application(request, application_id):
    """Withdraw job application"""
    application = get_object_or_404(
        JobApplication,
        id=application_id,
        applicant=request.user
    )
    
    if application.status in ['accepted', 'rejected']:
        return Response({
            'error': 'Cannot withdraw application with current status'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    application.status = 'withdrawn'
    application.save(update_fields=['status'])
    
    return Response({
        'message': 'Application withdrawn successfully'
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def job_categories(request):
    """Get available job categories with counts"""
    from apps.search.models import Category
    
    categories = Category.objects.filter(
        is_active=True,
        level=0  # Top-level categories only
    ).annotate(
        job_count=Count('job')
    ).order_by('order', 'name')
    
    category_data = [{
        'id': cat.id,
        'name': cat.name,
        'slug': cat.slug,
        'job_count': cat.job_count,
        'icon': cat.icon
    } for cat in categories]
    
    return Response({
        'categories': category_data
    })
