from django.core.management.base import BaseCommand
from users.models import User
import secrets


class Command(BaseCommand):
    help = '创建超级用户'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, default='admin', help='用户名')
        parser.add_argument('--email', type=str, default='admin@example.com', help='邮箱')
        parser.add_argument('--password', type=str, help='密码；不传时自动生成安全随机密码')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password'] or secrets.token_urlsafe(16)

        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'用户 {username} 已存在')
            )
            return

        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            role='admin'
        )

        self.stdout.write(
            self.style.SUCCESS(f'成功创建超级用户: {username}')
        )
        if not options['password']:
            self.stdout.write(
                self.style.WARNING(f'已自动生成初始密码，请立即妥善保存并在首次登录后修改: {password}')
            )
