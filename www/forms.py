from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import *


class UserForm(UserCreationForm):
    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'first_name',  # Добавлено
            'last_name',  # Добавлено
            'telephone',
            'department',
            'position',
            'password1',
            'password2'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Начальные значения для должностей
        self.fields['position'].queryset = Position.objects.none()

        # Динамическая загрузка должностей при наличии отдела в данных
        if 'department' in self.data:
            try:
                department_id = int(self.data.get('department'))
                self.fields['position'].queryset = Position.objects.filter(
                    department_id=department_id
                ).order_by('title')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.department:
            # Для существующих объектов
            self.fields['position'].queryset = self.instance.department.positions.order_by('title')


class UserProfileForm(UserChangeForm):
    first_name = forms.CharField(max_length=100, label="Имя")
    last_name = forms.CharField(max_length=100, label="Фамилия")
    telephone = forms.CharField(max_length=15, label="Телефон")
    avatar = forms.ImageField(required=False, label="Аватар")

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'telephone', 'avatar']


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'due_date', 'status', 'file_attachment', 'user']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)

        if current_user:
            if current_user.role.name == ROLE_ADMIN:
                self.fields['user'].queryset = User.objects.all()
            elif current_user.role.name == ROLE_MANAGER and current_user.department:
                self.fields['user'].queryset = User.objects.filter(department=current_user.department)
            else:
                self.fields['user'].queryset = User.objects.none()

class TaskFileUploadForm(forms.Form):
    file_attachment = forms.FileField(
        required=False,
        label='Прикрепить файл'
    )


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['title', 'file', 'category']



class SearchForm(forms.Form):
    query = forms.CharField(required=False, label='Поиск', max_length=100)

class ApplicationForm(forms.Form):
    name = forms.CharField(label='ФИО', max_length=100)
    email = forms.EmailField(label='Электронная почта')
    phone = forms.CharField(label='Телефон', max_length=20)