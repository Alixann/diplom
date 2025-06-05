from django.conf.urls.static import static
from django.urls import path

from diplomka import settings
from .views import *

urlpatterns = [
    path('', index, name='index'),
    path('main/', Home.as_view(), name='main'),
    path('register/', UserCreate.as_view(), name='register'),
    path('login/', Login.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('task/', TaskListView.as_view(), name='task'),  # Страница задач
    path('task_create/', TaskCreateView.as_view(), name='task_create'),
    path('task/<int:pk>/', TaskDetailView.as_view(), name='task_detail'),
    path('tasks/<int:pk>/delete/', TaskDeleteView.as_view(), name='task_delete'),
    path('documents/', DocumentListView.as_view(), name='documents'),
    path('documents/upload/', DocumentUploadView.as_view(), name='upload_document'),
    path('search/', search, name='search'),
    path('departments/', DepartmentListView.as_view(), name='department_list'),  # Список отделов
    path('departments/<int:pk>/', DepartmentDetailView.as_view(), name='department_detail'),  # Страница отдела
    path('profile/', profile_view, name='profile'),  # Просмотр профиля
    path('profile/edit/', profile_edit, name='profile_edit'),  # Редактирование профиля
    path('chat/<str:username>/', ChatView.as_view(), name='chat'),
    path('chats/', chat_list_view, name='chats'),
    path('message/delete/<int:message_id>/', DeleteMessageView.as_view(), name='delete_message'),
    path('message/edit/<int:message_id>/', EditMessageView.as_view(), name='edit_message'),
    path('users/<str:username>/', user_profile_view, name='user_profile'),
    path('admin-panel/', admin_panel, name='admin_panel'),
    path('department/add/', add_department, name='add_department'),
    path('department/<int:pk>/edit/', edit_department, name='edit_department'),
    path('department/<int:pk>/delete/', delete_department, name='delete_department'),
    path('admin-panel/user/<int:pk>/edit/', edit_user, name='edit_user'),
    path('admin-panel/user/<int:pk>/delete/', delete_user, name='delete_user'),
    path('admin-panel/documents/<int:pk>/edit/', edit_document, name='edit_document'),
    path('admin-panel/documents/<int:pk>/delete/', delete_document, name='delete_document'),
    path('load-positions/', LoadPositionsView.as_view(), name='load_positions'),
    path('toggle-role/<int:user_id>/', toggle_user_role, name='toggle_role'),
    path('positions/add/', add_position, name='add_position'),
    path('positions/<int:pk>/edit/', edit_position, name='edit_position'),
    path('positions/<int:pk>/delete/', delete_position, name='delete_position'),
    path('send_application/', send_application, name='send_application'),
    path('ajax/load-users/', LoadUsersView.as_view(), name='ajax_load_users'),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
