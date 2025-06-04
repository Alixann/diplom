from django.contrib.auth.models import AbstractUser
from django.db import models
from datetime import timedelta
from django.utils import timezone


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    def get_leader(self):
        manager_role = Role.objects.filter(name=ROLE_MANAGER).first()
        return User.objects.filter(department=self, role=manager_role).first()

class Position(models.Model):
    title = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='positions')

    def __str__(self):
        return f"{self.title} ({self.department.name})"


class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


# Константы для ролей
ROLE_EMPLOYEE = "Сотрудник"
ROLE_MANAGER = "Руководитель"
ROLE_ADMIN = "Администратор"


class User(AbstractUser):
    telephone = models.CharField(max_length=15)
    position = models.ForeignKey(
        Position,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Должность"
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Отдел"
    )
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    first_name = models.CharField(max_length=150, verbose_name="Имя")
    last_name = models.CharField(max_length=150, verbose_name="Фамилия")
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Роль"
    )

    def save(self, *args, **kwargs):
        if not self.pk and not self.role:
            employee_role, _ = Role.objects.get_or_create(name=ROLE_EMPLOYEE)
            self.role = employee_role
        if self.is_superuser and not self.role:
            admin_role, _ = Role.objects.get_or_create(name=ROLE_ADMIN)
            self.role = admin_role

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Message(models.Model):
    from_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    to_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_messages'
    )
    content = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to='chat_files/', blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    edited = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Message from {self.from_user} to {self.to_user}"


class Task(models.Model):
    STATUS_CHOICES = [
        ('new', 'Новая'),
        ('in_progress', 'В процессе'),
        ('completed', 'Завершена'),
    ]
    title = models.CharField(max_length=255)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tasks")
    file_attachment = models.FileField(upload_to='task_files/', blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new'
    )
    completed_comment = models.TextField(blank=True, null=True)
    due_date = models.DateField(null=True, blank=True)  # Добавлено поле даты
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title


class DocumentCategory(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Название категории")

    class Meta:
        verbose_name = "Категория документов"
        verbose_name_plural = "Категории документов"

    def __str__(self):
        return self.name


class Document(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255, verbose_name="Название документа")
    file = models.FileField(upload_to='documents/%Y/%m/%d/', verbose_name="Файл")
    category = models.ForeignKey(
        DocumentCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Категория"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")
    description = models.TextField(blank=True, null=True, verbose_name="Описание")

    class Meta:
        verbose_name = "Документ"
        verbose_name_plural = "Документы"
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.title

    def get_file_extension(self):
        return self.file.name.split('.')[-1].upper()


