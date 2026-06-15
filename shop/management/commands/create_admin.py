from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = "Create default admin user"

    def handle(self, *args, **options):
        username = "admin"
        password = "admin123"
        email = "admin@fashionhub.com"
        
        user = User.objects.filter(username=username).first()
        if not user:
            User.objects.create_superuser(
                username=username, email=email, password=password
            )
            self.stdout.write(
                self.style.SUCCESS(f"Admin user created: {username} / {password}")
            )
        else:
            # Force update password to ensure login works on Render
            user.set_password(password)
            user.is_superuser = True
            user.is_staff = True
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Admin password reset to: {password}"))
