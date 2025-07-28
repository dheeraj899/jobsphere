import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from faker import Faker
from django.utils.text import slugify
from apps.profile.models import UserProfile, Experience, About, Contact
from apps.map.models import Region, Location, LocationHistory
from apps.search.models import Category, SearchQuery, PopularSearch, SearchSuggestion, SavedSearch
from apps.jobs.models import Job, JobApplication, JobView, SavedJob
from apps.messaging.models import Notification
from apps.analytics.models import ResponseTime

class Command(BaseCommand):
    help = 'Seed database with mock data'

    def handle(self, *args, **options):
        fake = Faker()
        self.stdout.write('Deleting old data...')
        # Clear existing data
        ResponseTime.objects.all().delete()
        Notification.objects.all().delete()
        SavedSearch.objects.all().delete()
        SearchSuggestion.objects.all().delete()
        PopularSearch.objects.all().delete()
        SearchQuery.objects.all().delete()
        Category.objects.all().delete()
        JobView.objects.all().delete()
        JobApplication.objects.all().delete()
        Job.objects.all().delete()
        LocationHistory.objects.all().delete()
        Location.objects.all().delete()
        Region.objects.all().delete()
        Experience.objects.all().delete()
        About.objects.all().delete()
        Contact.objects.all().delete()
        UserProfile.objects.all().delete()
        User.objects.exclude(is_superuser=True).delete()

        self.stdout.write('Creating users and profiles...')
        users = []
        for _ in range(10):
            username = fake.user_name()
            user = User.objects.create_user(
                username=username,
                email=fake.email(),
                password='password'
            )
            users.append(user)
            UserProfile.objects.create(user=user, bio=fake.text(max_nb_chars=200), location=fake.city())
            About.objects.create(user=user, summary=fake.paragraph(), skills='Python, Django', interests='Coding', languages='English', years_of_experience=random.randint(1,10))
            Contact.objects.create(
                user=user,
                primary_email=user.email,
                primary_phone=fake.phone_number()[:20],
                city=fake.city(),
                country=fake.country()
            )
            for _ in range(2):
                Experience.objects.create(user=user, title=fake.job(), company=fake.company(), start_date=fake.date_this_decade(), end_date=None, is_current=True)

        from django.db.utils import IntegrityError
        self.stdout.write('Creating regions and locations...')
        regions = []
        while len(regions) < 5:
            name = fake.state()
            code = fake.state_abbr()
            try:
                region = Region.objects.create(name=name, code=code, country='USA')
            except IntegrityError:
                continue
            regions.append(region)
        locations = []
        for _ in range(20):
            region = random.choice(regions)
            loc = Location.objects.create(name=fake.city(), city=fake.city(), state_province=fake.state(), country='USA', latitude=fake.latitude(), longitude=fake.longitude(), location_type='job', region=region, is_verified=True)
            locations.append(loc)
        for user in users:
            for _ in range(3):
                LocationHistory.objects.create(user=user, location=random.choice(locations), search_query=fake.word(), search_context='job_search')

        self.stdout.write('Creating search data...')
        categories = [Category.objects.create(name=f'Category {_}', slug=f'category-{_}') for _ in range(5)]
        for user in users:
            for _ in range(5):
                sq = SearchQuery.objects.create(user=user, query_text=fake.word(), normalized_query=fake.word(), session_id=fake.uuid4(), ip_address=fake.ipv4(), search_type='job_search')
                PopularSearch.objects.get_or_create(query_text=sq.query_text, defaults={'search_count': random.randint(1,100)})
                SearchSuggestion.objects.create(text=fake.word(), suggestion_type='query')
                SavedSearch.objects.create(user=user, name=fake.word(), query_text=fake.word(), email_alerts=False, alert_frequency='daily')

        self.stdout.write('Creating job data...')
        jobs = []
        for _ in range(20):
            title = fake.job()
            company = fake.company()
            # generate unique slug
            base_slug = slugify(f"{title}-{company}")
            slug = base_slug
            counter = 1
            while Job.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            job = Job.objects.create(
                title=title,
                company=company,
                description=fake.text(),
                requirements=fake.text(),
                benefits=fake.text(),
                job_type='full_time',
                experience_level='entry',
                category='Tech',
                skills_required='Python',
                salary_min=50000,
                salary_max=100000,
                salary_currency='USD',
                salary_type='yearly',
                slug=slug,
                location=random.choice(locations),
                is_remote=False,
                posted_by=random.choice(users)
            )
            jobs.append(job)
        for user in users:
            for _ in range(3):
                job = random.choice(jobs)
                JobApplication.objects.create(job=job, applicant=user)
                JobView.objects.create(job=job, user=user, ip_address=fake.ipv4(), user_agent=fake.user_agent(), referrer=fake.url(), source='direct')
                SavedJob.objects.create(job=job, user=user)

        self.stdout.write('Creating messaging and analytics data...')
        for user in users:
            for _ in range(5):
                Notification.objects.create(user=user, notification_type='info', title=fake.sentence(), message=fake.text())
                ResponseTime.objects.create(user=user, endpoint='/api/test', http_method='GET', endpoint_category='test', response_time_ms=random.randint(50,500), db_query_time_ms=random.randint(10,100), db_query_count=random.randint(1,5), cache_hit=random.choice([True,False]), status_code=200, response_size_bytes=random.randint(500,2000), ip_address=fake.ipv4(), user_agent=fake.user_agent(), server_name='local', process_id=1, has_error=False, error_type='', error_message='')

        self.stdout.write(self.style.SUCCESS('Database seeding complete!')) 