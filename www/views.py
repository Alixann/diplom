from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.db.models import Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.timezone import localtime
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, TemplateView, View, ListView, DetailView, DeleteView
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse, reverse_lazy
from .models import ROLE_EMPLOYEE, ROLE_MANAGER, ROLE_ADMIN

from .forms import *
from .models import *


# Create your views here.

class UserCreate(CreateView):
    model = User
    form_class = UserForm
    template_name = 'register.html'

    def form_valid(self, form):
        self.object = form.save()
        login(self.request, self.object)
        return redirect('main')


class Login(LoginView):
    template_name = 'login.html'
    authentication_form = AuthenticationForm


class LogoutView(View):
    def get(self, request):
        logout(self.request)
        return redirect('login')


class LoadPositionsView(View):
    def get(self, request):
        department_id = request.GET.get('department_id')
        positions = Position.objects.filter(
            department_id=department_id
        ).order_by('title')
        return JsonResponse(
            {'positions': list(positions.values('id', 'title'))}
        )




def toggle_user_role(request, user_id):
    # Проверяем, что текущий пользователь - администратор
    if not request.user.role or request.user.role.name != ROLE_ADMIN:
        messages.error(request, "Недостаточно прав для выполнения этого действия")
        return redirect('main')

    user = get_object_or_404(User, id=user_id)

    if user.role.name == ROLE_EMPLOYEE:
        # Назначаем руководителем
        manager_role = Role.objects.get(name=ROLE_MANAGER)
        user.role = manager_role
        user.save()
        messages.success(request, f"{user.get_full_name()} назначен(а) руководителем")
    elif user.role.name == ROLE_MANAGER:
        # Возвращаем в сотрудники
        employee_role = Role.objects.get(name=ROLE_EMPLOYEE)
        user.role = employee_role
        user.save()
        messages.success(request, f"{user.get_full_name()} возвращен(а) в сотрудники")
    else:
        messages.warning(request, "Нельзя изменить роль администратора")

    return redirect('user_profile', username=user.username)


# Просмотр профиля
@login_required
def profile_view(request):
    messages = Message.objects.filter(
        Q(from_user=request.user) | Q(to_user=request.user)
    ).order_by('-timestamp')

    chat_data = {}

    for msg in messages:
        other_user = msg.to_user if msg.from_user == request.user else msg.from_user
        if other_user not in chat_data:
            chat_data[other_user] = {
                'user': other_user,
                'last_message': msg.content or '[Файл]',
                'timestamp': localtime(msg.timestamp),
            }


    tasks = Task.objects.filter(user=request.user).order_by('due_date')

    return render(request, 'profile.html', {
        'user': request.user,
        'chat_users': chat_data.values(),
        'tasks': tasks,  # 🆕 передаём задачи в шаблон
    })



# Редактирование профиля
@login_required
def profile_edit(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'profile_edit.html', {'form': form})



@login_required
def user_profile_view(request, username):
    user = get_object_or_404(User, username=username)
    is_own_profile = (request.user == user)
    return render(request, 'user_profile.html', {
        'user_profile': user,
        'is_own_profile': is_own_profile,
        'ROLE_ADMIN': ROLE_ADMIN,  # Добавлено
        'ROLE_MANAGER': ROLE_MANAGER,  # Добавлено
        'ROLE_EMPLOYEE': ROLE_EMPLOYEE,  # Добавлено
    })


# Отправка сообщений
class ChatView(LoginRequiredMixin, View):
    template_name = 'chat.html'

    def get(self, request, username):
        other_user = get_object_or_404(User, username=username)
        messages = Message.objects.filter(
            models.Q(from_user=request.user, to_user=other_user) |
            models.Q(from_user=other_user, to_user=request.user)
        ).order_by('timestamp')

        Message.objects.filter(
            from_user=other_user,
            to_user=request.user,
            is_read=False
        ).update(is_read=True)

        return render(request, self.template_name, {
            'other_user': other_user,
            'messages': messages
        })

    def post(self, request, username):
        other_user = get_object_or_404(User, username=username)
        content = request.POST.get('content')
        file = request.FILES.get('file')
        Message.objects.create(
            from_user=request.user,
            to_user=other_user,
            content=content,
            file=file
        )

        return redirect(reverse('chat', kwargs={'username': username}) + '#bottom')


class DeleteMessageView(LoginRequiredMixin, View):
    def post(self, request, message_id):
        message = get_object_or_404(Message, id=message_id)

        if message.from_user != request.user:
            return redirect('chat', username=message.to_user.username)

        other_user = message.to_user if message.from_user == request.user else message.from_user
        message.delete()

        return redirect('chat', username=other_user.username)


class EditMessageView(LoginRequiredMixin, View):
    template_name = 'chat.html'

    def get(self, request, message_id):
        message = get_object_or_404(Message, id=message_id)
        if message.from_user != request.user:
            return redirect('chat', username=message.to_user.username)
        other_user = message.to_user if message.from_user == request.user else message.from_user
        messages = Message.objects.filter(
            models.Q(from_user=request.user, to_user=other_user) |
            models.Q(from_user=other_user, to_user=request.user)
        ).order_by('timestamp')

        return render(request, self.template_name, {
            'other_user': other_user,
            'messages': messages,
            'edit_message_id': message_id,
            'edit_message_content': message.content
        })

    def post(self, request, message_id):
        message = get_object_or_404(Message, id=message_id)
        if message.from_user != request.user:
            return redirect('chat', username=message.to_user.username)

        message.content = request.POST.get('content')
        message.edited = True
        message.save()

        return redirect('chat', username=message.to_user.username)



class Home(LoginRequiredMixin, TemplateView):
    template_name = 'main.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['my_task_count'] = Task.objects.filter(user=user).count()

        if user.role and user.role.name == ROLE_MANAGER and user.department:
            dept = user.department
            employees_qs = User.objects.filter(department=dept)
            context['dept_employee_count'] = employees_qs.count()
            dept_tasks_qs = Task.objects.filter(user__department=dept)
            context['dept_task_count'] = dept_tasks_qs.count()
            context['dept_new_tasks'] = dept_tasks_qs.filter(status='new').count()
            context['dept_in_progress_tasks'] = dept_tasks_qs.filter(status='in_progress').count()
            context['dept_completed_tasks'] = dept_tasks_qs.filter(status='completed').count()
            context['is_manager'] = True
            context['manager_department'] = dept
        else:
            context['is_manager'] = False

        if user.is_superuser:
            departments = Department.objects.all()
            department_stats = []
            for dept in departments:
                dept_tasks = Task.objects.filter(user__department=dept)
                department_stats.append({
                    'id': dept.id,
                    'name': dept.name,
                    'manager': dept.get_leader().get_full_name() if dept.get_leader() else '—',
                    'task_count': dept_tasks.count(),
                })
            context['is_admin'] = True
            context['department_stats'] = department_stats
        else:
            context['is_admin'] = False

        return context


def index(request):
    return render(request, 'index.html')


class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = 'task.html'
    context_object_name = 'tasks'

    def get_queryset(self):
        queryset = super().get_queryset().filter(user=self.request.user)
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        date = self.request.GET.get('date')
        if date:
            queryset = queryset.filter(due_date=date)
        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_status'] = self.request.GET.get('status', '')
        context['current_date'] = self.request.GET.get('date', '')
        return context


class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = 'task_create.html'
    success_url = reverse_lazy('task')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['current_user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        return super().form_valid(form)


class TaskDetailView(LoginRequiredMixin, DetailView):
    model = Task
    template_name = 'task_detail.html'
    context_object_name = 'task'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = TaskFileUploadForm()
        return context

    def post(self, request, *args, **kwargs):
        task = self.get_object()
        if 'action' in request.POST and request.POST['action'] == 'change_status':
            new_status = request.POST.get('status')
            if new_status in ['in_progress', 'completed']:
                task.status = new_status
                if new_status == 'completed':
                    task.completed_at = timezone.now()
                task.save()
                return redirect('task_detail', pk=task.pk)
        elif 'action' in request.POST and request.POST['action'] == 'complete_task':
            form = TaskFileUploadForm(request.POST, request.FILES)
            comment = request.POST.get('comment', '').strip()
            file_attached = 'file_attachment' in request.FILES and request.FILES['file_attachment']
            if not comment and not file_attached:
                form.add_error(None, 'Необходимо заполнить комментарий или прикрепить файл!')
                context = self.get_context_data()
                context['form'] = form
                return self.render_to_response(context)
            if form.is_valid():
                if file_attached:
                    task.file_attachment = request.FILES['file_attachment']
                task.completed_comment = comment
                task.status = 'completed'
                task.completed_at = timezone.now()
                task.save()
                return redirect('task_detail', pk=task.pk)

        return super().get(request, *args, **kwargs)


class TaskDeleteView(LoginRequiredMixin,DeleteView):
    model = Task
    success_url = reverse_lazy('task')

    def dispatch(self, request, *args, **kwargs):
        task = self.get_object()
        if task.user != request.user:
            return HttpResponseForbidden("Вы не можете удалить эту задачу.")
        if task.status != 'completed':
            return HttpResponseForbidden("Удаление разрешено только для завершённых задач.")
        return super().dispatch(request, *args, **kwargs)



class DepartmentListView(LoginRequiredMixin, ListView):
    model = Department
    template_name = 'department_list.html'
    context_object_name = 'departments'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        departments = context['departments']
        for department in departments:
            department.employees = User.objects.filter(department=department)
            department.leader = department.employees.filter(role__name=ROLE_MANAGER).first()
        return context


class DepartmentDetailView(LoginRequiredMixin,DetailView):
    model = Department
    template_name = 'department_detail.html'
    context_object_name = 'department'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        department = self.get_object()
        context['employees'] = User.objects.filter(department=department).select_related('position')
        return context


class DocumentListView(LoginRequiredMixin, ListView):
    model = Document
    template_name = 'documents.html'
    context_object_name = 'documents'
    paginate_by = 10

    def get_queryset(self):
        queryset = Document.objects.all()
        category_id = self.request.GET.get('category')
        if category_id and category_id != 'all':
            queryset = queryset.filter(category_id=category_id)

        return queryset.order_by('-uploaded_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = DocumentCategory.objects.all()
        context['selected_category'] = self.request.GET.get('category', 'all')
        return context


class DocumentUploadView(View, LoginRequiredMixin):
    def get(self, request):
        form = DocumentForm()
        return render(request, 'upload_document.html', {'form': form})

    def post(self, request):
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.user = request.user
            document.save()
            return redirect('documents')

        return render(request, 'upload_document.html', {'form': form})


@login_required
def search(request):
    query = request.GET.get('query', '').strip()
    employees = User.objects.none()
    documents = Document.objects.none()

    if query:
        employees = User.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(username__icontains=query) |
            Q(position__title__icontains=query)
        ).select_related('position')

        documents = Document.objects.filter(title__icontains=query).order_by('-uploaded_at')

    return render(request, 'search_results.html', {
        'query': query,
        'employees': employees,
        'documents': documents,
    })



@login_required
def chat_list_view(request):
    user = request.user
    messages = Message.objects.filter(Q(from_user=user) | Q(to_user=user))
    interlocutors = (
        messages
        .values('from_user', 'to_user')
        .distinct()
    )
    user_ids = set()
    for m in interlocutors:
        uid = m['from_user'] if m['from_user'] != user.id else m['to_user']
        user_ids.add(uid)
    chat_users = []
    for uid in user_ids:
        chat_user = User.objects.get(pk=uid)

        last_msg = Message.objects.filter(
            Q(from_user=user, to_user=chat_user) |
            Q(from_user=chat_user, to_user=user)
        ).order_by('-timestamp').first()

        unread_count = Message.objects.filter(
            from_user=chat_user,
            to_user=user,
            is_read=False
        ).count()

        chat_users.append({
            'user': chat_user,
            'last_message': last_msg.content if last_msg else '',
            'timestamp': last_msg.timestamp if last_msg else None,
            'last_message_sender': last_msg.from_user if last_msg else None,
            'unread_count': unread_count,
        })

    chat_users = sorted(chat_users, key=lambda x: x['timestamp'] or '', reverse=True)

    return render(request, 'chats.html', {
        'chat_users': chat_users,
    })





@login_required
def admin_panel(request):
    departments = Department.objects.prefetch_related('positions').all()
    users = User.objects.select_related('department').all()
    documents = Document.objects.select_related('user').all().order_by('-uploaded_at')
    return render(request, 'admin_panel.html', {
        'departments': departments,
        'users': users,
        'documents': documents,
    })


def add_department(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            Department.objects.create(name=name)
            messages.success(request, 'Отдел добавлен')
        return redirect('admin_panel')
    return render(request, 'department_form.html', {'action': 'Добавить'})

def edit_department(request, pk):
    department = get_object_or_404(Department, pk=pk)
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            department.name = name
            department.save()
            messages.success(request, 'Отдел обновлён')
        return redirect('admin_panel')
    return render(request, 'department_form.html', {'action': 'Изменить', 'department': department})




def delete_department(request, pk):
    department = get_object_or_404(Department, pk=pk)
    department.delete()
    messages.success(request, 'Отдел удалён')
    return redirect('admin_panel')


def edit_user(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UserForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Пользователь обновлён.')
            return redirect('admin_panel')
    else:
        form = UserForm(instance=user)

    return render(request, 'edit_user.html', {'form': form, 'user_obj': user})



def delete_user(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, "Нельзя удалить себя.")
    else:
        user.delete()
        messages.success(request, 'Пользователь удалён.')
    return redirect('admin_panel')


def edit_document(request, pk):
    document = get_object_or_404(Document, pk=pk)
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES, instance=document)
        if form.is_valid():
            form.save()
            return redirect('admin_panel')
    else:
        form = DocumentForm(instance=document)
    return render(request, 'edit_document.html', {'form': form})




def delete_document(request, pk):
    document = get_object_or_404(Document, pk=pk)
    document.delete()
    return redirect('admin_panel')


def add_position(request):
    # Форма проста: выбираем отдел и вводим название
    if request.method == 'POST':
        department_id = request.POST.get('department')
        title = request.POST.get('title')
        if department_id and title:
            dept = get_object_or_404(Department, pk=department_id)
            Position.objects.create(department=dept, title=title)
            messages.success(request, 'Должность добавлена')
        return redirect('admin_panel')

    # GET: показываем форму
    return render(request, 'position_form.html', {
        'action': 'Добавить',
        'departments': Department.objects.all(),
    })

def edit_position(request, pk):
    pos = get_object_or_404(Position, pk=pk)
    if request.method == 'POST':
        department_id = request.POST.get('department')
        title = request.POST.get('title')
        if department_id and title:
            pos.department = get_object_or_404(Department, pk=department_id)
            pos.title = title
            pos.save()
            messages.success(request, 'Должность обновлена')
        return redirect('admin_panel')

    return render(request, 'position_form.html', {
        'action': 'Изменить',
        'position': pos,
        'departments': Department.objects.all(),
    })



def delete_position(request, pk):
    pos = get_object_or_404(Position, pk=pk)
    pos.delete()
    messages.success(request, 'Должность удалена')
    return redirect('admin_panel')



def send_application(request):
    if request.method == 'POST':
        form = ApplicationForm(request.POST)
        if form.is_valid():
            # Получаем данные из формы
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            phone = form.cleaned_data['phone']

            # Тема и текст письма
            subject = 'Новая заявка с сайта'
            message = f'''
            Поступила новая заявка:

            ФИО: {name}
            Email: {email}
            Телефон: {phone}
            '''

            # Отправка письма
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [settings.ADMIN_EMAIL],  # Ваш email
                fail_silently=False,
            )

            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    return JsonResponse({'success': False, 'errors': 'Неверный метод запроса'})