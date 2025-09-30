from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Create test users with different roles'

    def handle(self, *args, **options):
        # Create test users
        users_data = [
            {'username': 'testuser', 'password': 'testpass123', 'role': 'user'},
            {'username': 'moderator', 'password': 'modpass123', 'role': 'moderator'},
            {'username': 'admin_user', 'password': 'adminpass123', 'role': 'admin'},
        ]
        
        for user_data in users_data:
            username = user_data['username']
            password = user_data['password']
            role = user_data['role']
            
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    role=role
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Created user: {username} with role: {role}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'User {username} already exists')
                )
        
        self.stdout.write(
            self.style.SUCCESS('Test users creation completed!')
        )
